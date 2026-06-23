from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import tempfile

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.core.config import get_settings
from app.database.mongodb import get_database
from app.dependencies.auth_dependency import require_student
from app.models.student_profile_model import (
    create_profile_document,
    profile_to_public,
)
from app.models.course_resource_model import VALID_FILE_TYPES
from app.schemas.student_profile_schema import (
    StudentProfileCreate,
    StudentProfileResponse,
    StudentProfileUpdate,
)
from app.services.document_preview_service import preview_student_profile_from_file
from app.services.file_extraction_service import detect_file_type
from app.utils.objectid import to_object_id


router = APIRouter(prefix="/api/student-profiles", tags=["Student Profiles"])


async def _save_preview_upload(file: UploadFile, file_type: str) -> Path:
    settings = get_settings()
    content = await file.read()
    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            f"File exceeds {settings.max_upload_size_mb}MB limit",
        )
    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_type}") as temporary:
        temporary.write(content)
        return Path(temporary.name)


@router.post("", response_model=StudentProfileResponse, status_code=status.HTTP_201_CREATED)
async def create_profile(
    payload: StudentProfileCreate,
    current_user: dict = Depends(require_student),
) -> StudentProfileResponse:
    db = get_database()
    profile_doc = create_profile_document(
        student_id=current_user["_id"],
        source_type="manual_form",
        intent_text=payload.intent_text,
        question_answers=payload.question_answers,
        career_goal=payload.career_goal,
        current_level=payload.current_level,
        current_skills=payload.current_skills,
        desired_skills=payload.desired_skills,
        interested_topics=payload.interested_topics,
        hours_per_week=payload.hours_per_week,
        learning_format=payload.learning_format,
    )
    result = await db.student_profiles.insert_one(profile_doc)
    profile_doc["_id"] = result.inserted_id
    return profile_to_public(profile_doc)


@router.get("/me", response_model=list[StudentProfileResponse])
async def list_my_profiles(
    current_user: dict = Depends(require_student),
) -> list[StudentProfileResponse]:
    db = get_database()
    profiles = (
        await db.student_profiles.find({"student_id": current_user["_id"]})
        .sort("created_at", -1)
        .to_list(length=None)
    )
    return [profile_to_public(profile) for profile in profiles]


@router.post("/extract-preview")
async def extract_profile_preview(
    file: UploadFile = File(...),
    _: dict = Depends(require_student),
) -> dict[str, object]:
    file_type = detect_file_type(file.filename or "")
    if file_type not in VALID_FILE_TYPES:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Only pdf, pptx, docx files are allowed",
        )

    temporary_path = await _save_preview_upload(file, file_type)
    try:
        return preview_student_profile_from_file(str(temporary_path), file_type)
    finally:
        temporary_path.unlink(missing_ok=True)


@router.put("/{profile_id}", response_model=StudentProfileResponse)
async def update_profile(
    profile_id: str,
    payload: StudentProfileUpdate,
    current_user: dict = Depends(require_student),
) -> StudentProfileResponse:
    db = get_database()
    oid = to_object_id(profile_id, "profile_id")
    profile = await db.student_profiles.find_one({"_id": oid})
    if profile is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Profile not found")
    if str(profile["student_id"]) != str(current_user["_id"]):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not allowed to edit this profile")

    updates = payload.model_dump(exclude_unset=True)
    if updates:
        updates["updated_at"] = datetime.now(timezone.utc)
        await db.student_profiles.update_one({"_id": oid}, {"$set": updates})

    profile = await db.student_profiles.find_one({"_id": oid})
    return profile_to_public(profile)
