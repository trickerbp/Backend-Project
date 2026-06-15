from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.core.config import get_settings
from app.database.mongodb import get_database
from app.dependencies.auth_dependency import require_teacher_or_admin
from app.models.course_resource_model import (
    VALID_FILE_TYPES,
    create_resource_document,
    resource_to_public,
)
from app.services import course_resource_service
from app.services.file_extraction_service import detect_file_type
from app.schemas.course_resource_schema import CourseResourceResponse
from app.utils.objectid import to_object_id


router = APIRouter(tags=["Course Resources"])


def _is_owner_or_admin(course: dict, user: dict) -> bool:
    if user.get("role") == "admin":
        return True
    return str(course.get("teacher_id")) == str(user["_id"])


async def _load_course_for_write(course_id: str, user: dict) -> dict:
    db = get_database()
    course = await db.courses.find_one({"_id": to_object_id(course_id, "course_id")})
    if course is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Course not found")
    if not _is_owner_or_admin(course, user):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "Not allowed to manage resources for this course"
        )
    return course


@router.post(
    "/api/courses/{course_id}/resources",
    response_model=CourseResourceResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_resource(
    course_id: str,
    file: UploadFile = File(...),
    current_user: dict = Depends(require_teacher_or_admin),
) -> CourseResourceResponse:
    db = get_database()
    settings = get_settings()
    course = await _load_course_for_write(course_id, current_user)

    file_type = detect_file_type(file.filename or "")
    if file_type not in VALID_FILE_TYPES:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Only pdf, pptx, docx files are allowed",
        )

    content = await file.read()
    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            f"File exceeds {settings.max_upload_size_mb}MB limit",
        )

    upload_dir = Path(settings.upload_dir) / "course_resources"
    upload_dir.mkdir(parents=True, exist_ok=True)
    stored_name = f"{uuid.uuid4().hex}.{file_type}"
    stored_path = upload_dir / stored_name
    stored_path.write_bytes(content)

    resource_doc = create_resource_document(
        course_id=course["_id"],
        uploaded_by=current_user["_id"],
        file_name=stored_name,
        original_file_name=file.filename or stored_name,
        file_type=file_type,
        file_path=str(stored_path).replace("\\", "/"),
        file_size=len(content),
    )
    result = await db.course_resources.insert_one(resource_doc)
    resource_doc["_id"] = result.inserted_id
    return resource_to_public(resource_doc)


@router.get(
    "/api/courses/{course_id}/resources",
    response_model=list[CourseResourceResponse],
)
async def list_course_resources(
    course_id: str,
    current_user: dict = Depends(require_teacher_or_admin),
) -> list[CourseResourceResponse]:
    db = get_database()
    course = await _load_course_for_write(course_id, current_user)
    resources = (
        await db.course_resources.find({"course_id": course["_id"]})
        .sort("created_at", -1)
        .to_list(length=None)
    )
    return [resource_to_public(resource) for resource in resources]


@router.get("/api/resources/{resource_id}", response_model=CourseResourceResponse)
async def get_resource(
    resource_id: str,
    current_user: dict = Depends(require_teacher_or_admin),
) -> CourseResourceResponse:
    resource = await _load_resource_for_write(resource_id, current_user)
    return resource_to_public(resource)


@router.delete("/api/resources/{resource_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_resource(
    resource_id: str,
    current_user: dict = Depends(require_teacher_or_admin),
) -> None:
    db = get_database()
    resource = await _load_resource_for_write(resource_id, current_user)
    stored_path = Path(resource["file_path"])
    if stored_path.exists():
        stored_path.unlink()
    await db.course_resources.delete_one({"_id": resource["_id"]})


@router.post("/api/resources/{resource_id}/process", response_model=CourseResourceResponse)
async def process_resource(
    resource_id: str,
    current_user: dict = Depends(require_teacher_or_admin),
) -> CourseResourceResponse:
    db = get_database()
    resource = await _load_resource_for_write(resource_id, current_user)
    try:
        updated = await course_resource_service.process_resource(db, resource)
    except Exception as exc:  # noqa: BLE001 - surfaced as 422 with detail
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"Processing failed: {exc}",
        ) from exc
    return resource_to_public(updated)


async def _load_resource_for_write(resource_id: str, user: dict) -> dict:
    db = get_database()
    resource = await db.course_resources.find_one(
        {"_id": to_object_id(resource_id, "resource_id")}
    )
    if resource is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Resource not found")

    course = await db.courses.find_one({"_id": resource["course_id"]})
    if course is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Course not found")
    if not _is_owner_or_admin(course, user):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "Not allowed to access this resource"
        )
    return resource
