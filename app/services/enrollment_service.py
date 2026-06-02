from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from bson import ObjectId
from fastapi import HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from app.models.enrollment_model import (
    create_enrollment_document,
    enrollment_to_response,
)
from app.schemas.enrollment_schema import EnrollmentCreate
from app.utils.objectid import to_object_id


async def create_enrollment(
    db: AsyncIOMotorDatabase,
    student_id: ObjectId,
    payload: EnrollmentCreate,
) -> dict[str, Any]:
    class_id = to_object_id(payload.class_id, "class_id")
    class_doc = await db.classes.find_one({"_id": class_id})

    if class_doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Class not found",
        )

    if class_doc["status"] != "open":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Class is closed",
        )

    if class_doc.get("current_students", 0) >= class_doc["max_students"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Class is full",
        )

    existing = await db.enrollments.find_one(
        {
            "student_id": student_id,
            "class_id": class_id,
        },
    )
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Student already enrolled in this class",
        )

    enrollment_doc = create_enrollment_document(
        student_id=student_id,
        class_id=class_id,
        note=payload.note,
    )

    try:
        result = await db.enrollments.insert_one(enrollment_doc)
    except DuplicateKeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Student already enrolled in this class",
        ) from exc

    enrollment_doc["_id"] = result.inserted_id
    return enrollment_to_response(enrollment_doc)


async def approve_enrollment(
    db: AsyncIOMotorDatabase,
    enrollment_id: str,
    admin_id: ObjectId,
) -> dict[str, Any]:
    enrollment_object_id = to_object_id(enrollment_id, "enrollment_id")
    enrollment = await db.enrollments.find_one({"_id": enrollment_object_id})

    if enrollment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Enrollment not found",
        )

    if enrollment["status"] != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Enrollment has already been processed",
        )

    class_doc = await db.classes.find_one({"_id": enrollment["class_id"]})
    if class_doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Class not found",
        )

    if class_doc["status"] != "open":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Class is closed",
        )

    current_students = class_doc.get("current_students", 0)
    max_students = class_doc["max_students"]

    if current_students >= max_students:
        await db.classes.update_one(
            {"_id": class_doc["_id"]},
            {"$set": {"status": "closed", "updated_at": datetime.now(timezone.utc)}},
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Class is full",
        )

    now = datetime.now(timezone.utc)
    updated_enrollment = await db.enrollments.find_one_and_update(
        {"_id": enrollment_object_id, "status": "pending"},
        {
            "$set": {
                "status": "approved",
                "approved_by": admin_id,
                "updated_at": now,
            }
        },
        return_document=ReturnDocument.AFTER,
    )

    if updated_enrollment is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Enrollment has already been processed",
        )

    new_current_students = current_students + 1
    class_update = {
        "$inc": {"current_students": 1},
        "$set": {"updated_at": now},
    }
    if new_current_students >= max_students:
        class_update["$set"]["status"] = "closed"

    await db.classes.update_one({"_id": class_doc["_id"]}, class_update)
    return enrollment_to_response(updated_enrollment)


async def reject_enrollment(
    db: AsyncIOMotorDatabase,
    enrollment_id: str,
    admin_id: ObjectId,
) -> dict[str, Any]:
    enrollment_object_id = to_object_id(enrollment_id, "enrollment_id")
    now = datetime.now(timezone.utc)
    updated_enrollment = await db.enrollments.find_one_and_update(
        {"_id": enrollment_object_id, "status": "pending"},
        {
            "$set": {
                "status": "rejected",
                "approved_by": admin_id,
                "updated_at": now,
            }
        },
        return_document=ReturnDocument.AFTER,
    )

    if updated_enrollment is None:
        existing = await db.enrollments.find_one({"_id": enrollment_object_id})
        if existing is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Enrollment not found",
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Enrollment has already been processed",
        )

    return enrollment_to_response(updated_enrollment)
