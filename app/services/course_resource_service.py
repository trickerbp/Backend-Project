from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.config import get_settings
from app.services import text_cleaning_service as cleaner
from app.services import azure_document_ocr_service
from app.services.matching.core_engine import core_extractor
from app.services.processing_log_service import write_processing_log


async def _log(
    db: AsyncIOMotorDatabase,
    resource_id: ObjectId,
    course_id: ObjectId,
    step: str,
    status: str,
    message: str,
) -> None:
    await write_processing_log(db, resource_id, course_id, step, status, message)


async def _set_resource(
    db: AsyncIOMotorDatabase,
    resource_id: ObjectId,
    fields: dict[str, Any],
) -> None:
    fields["updated_at"] = datetime.now(timezone.utc)
    await db.course_resources.update_one({"_id": resource_id}, {"$set": fields})


async def process_resource(
    db: AsyncIOMotorDatabase,
    resource: dict[str, Any],
) -> dict[str, Any]:
    """Run the full extract -> clean -> extract-info -> sync pipeline.

    Returns the updated resource document. Failures are persisted on the
    resource (processing_status="failed", error_message) and re-raised so the
    caller can surface an error response.
    """
    resource_id = resource["_id"]
    course_id = resource["course_id"]
    file_path = resource["file_path"]
    file_type = resource["file_type"]
    await _set_resource(db, resource_id, {"processing_status": "processing"})

    try:
        raw_text = core_extractor.parse_document(file_path, file_type)
    except Exception as exc:  # noqa: BLE001 - persist and re-raise
        await _set_resource(
            db,
            resource_id,
            {"processing_status": "failed", "error_message": str(exc)},
        )
        await _log(db, resource_id, course_id, "extract_text", "failed", str(exc))
        raise

    await _set_resource(db, resource_id, {"raw_text": raw_text})
    await _log(db, resource_id, course_id, "extract_text", "success",
               f"Extracted {len(raw_text)} characters.")

    if _should_use_azure_ocr(raw_text, file_type):
        try:
            ocr_text = azure_document_ocr_service.extract_text(file_path)
        except Exception as exc:  # noqa: BLE001 - fallback failure should be explicit
            await _log(db, resource_id, course_id, "azure_document_ocr", "failed", str(exc))
        else:
            if len(ocr_text.strip()) > len(raw_text.strip()):
                raw_text = ocr_text
                await _set_resource(
                    db,
                    resource_id,
                    {
                        "raw_text": raw_text,
                        "ocr_provider": "azure_document_intelligence",
                    },
                )
                await _log(
                    db,
                    resource_id,
                    course_id,
                    "azure_document_ocr",
                    "success",
                    f"Extracted {len(raw_text)} characters with Azure OCR.",
                )

    cleaned = cleaner.clean_text(raw_text)
    await _set_resource(db, resource_id, {"cleaned_text": cleaned})
    await _log(db, resource_id, course_id, "clean_text", "success",
               f"Cleaned text length {len(cleaned)}.")

    if not cleaner.is_text_sufficient(cleaned):
        await _set_resource(db, resource_id, {"processing_status": "needs_ocr"})
        await _log(db, resource_id, course_id, "extract_course_info", "failed",
                   "Text too short, needs OCR.")
        return await db.course_resources.find_one({"_id": resource_id})

    info = core_extractor.extract_course_info(cleaned)
    await _set_resource(db, resource_id, info)
    await _log(db, resource_id, course_id, "extract_course_info", "success",
               "Extracted course info from text.")

    await _sync_course_metadata(db, course_id, info)
    await _log(db, resource_id, course_id, "update_course_metadata", "success",
               "Synced extracted metadata to course.")

    await _set_resource(db, resource_id, {"processing_status": "completed"})
    return await db.course_resources.find_one({"_id": resource_id})


async def _sync_course_metadata(
    db: AsyncIOMotorDatabase,
    course_id: ObjectId,
    info: dict[str, Any],
) -> None:
    """Union the newly extracted lists into the course document."""
    course = await db.courses.find_one({"_id": course_id})
    if course is None:
        return

    def merged(field: str, new_values: list[str]) -> list[str]:
        existing = course.get(field, []) or []
        result = list(existing)
        for value in new_values:
            if value not in result:
                result.append(value)
        return result

    update = {
        "extracted_skills": merged("extracted_skills", info.get("extracted_skills", [])),
        "extracted_topics": merged("extracted_topics", info.get("extracted_topics", [])),
        "extracted_objectives": merged(
            "extracted_objectives", info.get("extracted_objectives", [])
        ),
        "extracted_prerequisites": merged(
            "extracted_prerequisites", info.get("extracted_prerequisites", [])
        ),
        "tools": merged("tools", info.get("extracted_tools", [])),
        "updated_at": datetime.now(timezone.utc),
    }
    await db.courses.update_one({"_id": course_id}, {"$set": update})


def _should_use_azure_ocr(raw_text: str, file_type: str) -> bool:
    settings = get_settings()
    if not settings.use_azure_document_intelligence:
        return False
    if file_type not in {"pdf", "docx", "pptx"}:
        return False
    return len(raw_text.strip()) < settings.ocr_min_text_chars
