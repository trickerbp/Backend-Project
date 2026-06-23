
from __future__ import annotations

from typing import Optional

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.core.config import get_settings


mongo_client: Optional[AsyncIOMotorClient] = None
mongo_database: Optional[AsyncIOMotorDatabase] = None


async def connect_to_mongo() -> None:
    global mongo_client, mongo_database

    settings = get_settings()
    mongo_client = AsyncIOMotorClient(settings.mongodb_url)
    mongo_database = mongo_client[settings.mongodb_db_name]
    await create_indexes(mongo_database)


async def close_mongo_connection() -> None:
    global mongo_client, mongo_database

    if mongo_client is not None:
        mongo_client.close()
    mongo_client = None
    mongo_database = None


def get_database() -> AsyncIOMotorDatabase:
    if mongo_database is None:
        raise RuntimeError("MongoDB connection has not been initialized")
    return mongo_database


async def create_indexes(db: AsyncIOMotorDatabase) -> None:
    # users
    await db.users.create_index("email", unique=True)
    await db.users.create_index("role")

    # courses
    await db.courses.create_index("teacher_id")
    await db.courses.create_index("level")
    await db.courses.create_index("status")
    await db.courses.create_index("manual_tags")
    await db.courses.create_index("extracted_skills")
    await db.courses.create_index([("title", "text"), ("description", "text")])

    # course_resources
    await db.course_resources.create_index("course_id")
    await db.course_resources.create_index("uploaded_by")
    await db.course_resources.create_index("processing_status")
    await db.course_resources.create_index("file_type")
    await db.course_resources.create_index("extracted_skills")

    # student_profiles
    await db.student_profiles.create_index("student_id")
    await db.student_profiles.create_index("current_level")
    await db.student_profiles.create_index("desired_skills")
    await db.student_profiles.create_index("career_goal")

    # recommendations
    await db.recommendations.create_index("student_id")
    await db.recommendations.create_index("student_profile_id")
    await db.recommendations.create_index([("created_at", -1)])

    # recommendation_events
    await db.recommendation_events.create_index("student_id")
    await db.recommendation_events.create_index("course_id")
    await db.recommendation_events.create_index([("created_at", -1)])

    # processing_logs
    await db.processing_logs.create_index("resource_id")
    await db.processing_logs.create_index("course_id")
    await db.processing_logs.create_index([("created_at", -1)])
    await db.processing_logs.create_index("status")
