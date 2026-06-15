from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status

from app.database.mongodb import get_database
from app.dependencies.auth_dependency import require_student
from app.models.student_profile_model import (
    create_profile_document,
    profile_to_public,
)
from app.schemas.student_profile_schema import (
    StudentProfileCreate,
    StudentProfileResponse,
    StudentProfileUpdate,
)
from app.utils.objectid import to_object_id


router = APIRouter(prefix="/api/student-profiles", tags=["Student Profiles"])


@router.post("", response_model=StudentProfileResponse, status_code=status.HTTP_201_CREATED)
async def create_profile(
    payload: StudentProfileCreate,
    current_user: dict = Depends(require_student),
) -> StudentProfileResponse:
    db = get_database()
    profile_doc = create_profile_document(
        student_id=current_user["_id"],
        source_type="manual_form",
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
