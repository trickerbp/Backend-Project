
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
    await db.users.create_index("email", unique=True)
    await db.classes.create_index("class_name")
    await db.classes.create_index("status")
    await db.enrollments.create_index(
        [("student_id", 1), ("class_id", 1)],
        unique=True,
    )
    await db.enrollments.create_index("student_id")
    await db.enrollments.create_index("class_id")
    await db.enrollments.create_index("status")
