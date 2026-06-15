from __future__ import annotations

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.processing_log_model import (
    PROCESSING_LOGS_COLLECTION,
    create_log_document,
)


async def write_processing_log(
    db: AsyncIOMotorDatabase,
    resource_id: ObjectId | None,
    course_id: ObjectId | None,
    step: str,
    status: str,
    message: str,
) -> None:
    await db[PROCESSING_LOGS_COLLECTION].insert_one(
        create_log_document(resource_id, course_id, step, status, message)
    )
