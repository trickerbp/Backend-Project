from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import tempfile

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.core.config import get_settings
from app.database.mongodb import get_database
from app.dependencies.auth_dependency import (
    get_current_user,
    require_teacher_or_admin,
)
from app.models.course_model import (
    VALID_LEVELS,
    VALID_STATUSES,
    course_to_public,
    create_course_document,
)
from app.models.course_resource_model import VALID_FILE_TYPES
from app.schemas.course_schema import CourseCreate, CourseResponse, CourseUpdate
from app.services.document_preview_service import preview_course_from_file
from app.services.file_extraction_service import detect_file_type
from app.utils.objectid import to_object_id


router = APIRouter(prefix="/api/courses", tags=["Courses"])


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


def _is_owner_or_admin(course: dict, user: dict) -> bool:
    if user.get("role") == "admin":
        return True
    return str(course.get("teacher_id")) == str(user["_id"])


@router.get("", response_model=list[CourseResponse])
async def list_courses(
    current_user: dict = Depends(get_current_user),
) -> list[CourseResponse]:
    db = get_database()
    role = current_user.get("role")

    if role == "student":
        query = {"status": "active"}
    elif role == "teacher":
        query = {"teacher_id": current_user["_id"]}
    else:  # admin
        query = {}

    courses = await db.courses.find(query).sort("created_at", -1).to_list(length=None)
    return [course_to_public(course) for course in courses]


@router.get("/{course_id}", response_model=CourseResponse)
async def get_course(
    course_id: str,
    current_user: dict = Depends(get_current_user),
) -> CourseResponse:
    db = get_database()
    course = await db.courses.find_one({"_id": to_object_id(course_id, "course_id")})
    if course is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Course not found")

    if current_user.get("role") == "student" and course.get("status") != "active":
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Course not found")
    if current_user.get('role') == 'teacher' and not _is_owner_or_admin(course, current_user):
        raise HTTPException(status.HTTP_404_NOT_FOUND, 'Course not found')

    return course_to_public(course)


@router.post("", response_model=CourseResponse, status_code=status.HTTP_201_CREATED)
async def create_course(
    payload: CourseCreate,
    current_user: dict = Depends(require_teacher_or_admin),
) -> CourseResponse:
    db = get_database()

    if payload.level not in VALID_LEVELS:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid level")
    if payload.status not in VALID_STATUSES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid status")

    existing = await db.courses.find_one({"course_code": payload.course_code})
    if existing is not None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Course code already exists")

    teacher_id = current_user["_id"]
    if current_user.get('role') == 'admin':
        if not payload.teacher_id:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, 'teacher_id is required for admin-created courses')
        teacher_id = to_object_id(payload.teacher_id, 'teacher_id')
        teacher = await db.users.find_one({'_id': teacher_id, 'role': 'teacher'})
        if teacher is None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, 'Teacher not found')

    course_doc = create_course_document(
        title=payload.title,
        course_code=payload.course_code,
        description=payload.description,
        level=payload.level,
        teacher_id=teacher_id,
        target_goals=payload.target_goals,
        manual_tags=payload.manual_tags,
        tools=payload.tools,
        duration_hours=payload.duration_hours,
        status=payload.status,
    )
    result = await db.courses.insert_one(course_doc)
    course_doc["_id"] = result.inserted_id
    return course_to_public(course_doc)


@router.post("/extract-preview")
async def extract_course_preview(
    file: UploadFile = File(...),
    _: dict = Depends(require_teacher_or_admin),
) -> dict[str, object]:
    file_type = detect_file_type(file.filename or "")
    if file_type not in VALID_FILE_TYPES:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Only pdf, pptx, docx files are allowed",
        )

    temporary_path = await _save_preview_upload(file, file_type)
    try:
        return preview_course_from_file(str(temporary_path), file_type)
    finally:
        temporary_path.unlink(missing_ok=True)


@router.put("/{course_id}", response_model=CourseResponse)
async def update_course(
    course_id: str,
    payload: CourseUpdate,
    current_user: dict = Depends(require_teacher_or_admin),
) -> CourseResponse:
    db = get_database()
    oid = to_object_id(course_id, "course_id")
    course = await db.courses.find_one({"_id": oid})
    if course is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Course not found")
    if not _is_owner_or_admin(course, current_user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not allowed to edit this course")

    updates = payload.model_dump(exclude_unset=True)
    if 'teacher_id' in updates:
        if current_user.get('role') != 'admin':
            raise HTTPException(status.HTTP_403_FORBIDDEN, 'Only admin can change course teacher')
        teacher_id = to_object_id(updates.pop('teacher_id'), 'teacher_id')
        teacher = await db.users.find_one({'_id': teacher_id, 'role': 'teacher'})
        if teacher is None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, 'Teacher not found')
        updates['teacher_id'] = teacher_id
    if updates:
        updates["updated_at"] = datetime.now(timezone.utc)
        await db.courses.update_one({"_id": oid}, {"$set": updates})

    course = await db.courses.find_one({"_id": oid})
    return course_to_public(course)


@router.delete("/{course_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_course(
    course_id: str,
    current_user: dict = Depends(require_teacher_or_admin),
) -> None:
    db = get_database()
    oid = to_object_id(course_id, "course_id")
    course = await db.courses.find_one({"_id": oid})
    if course is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Course not found")
    if not _is_owner_or_admin(course, current_user):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "Not allowed to delete this course"
        )

    await db.course_resources.delete_many({"course_id": oid})
    await db.courses.delete_one({"_id": oid})
