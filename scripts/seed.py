from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.core.config import get_settings  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.database.mongodb import create_indexes  # noqa: E402


ADMIN_EMAIL = "admin@gmail.com"
STUDENT_EMAIL = "student@gmail.com"
DEFAULT_PASSWORD = "123456"


async def upsert_user(
    db: AsyncIOMotorDatabase,
    name: str,
    email: str,
    role: str,
) -> Any:
    now = datetime.now(timezone.utc)
    payload = {
        "name": name,
        "email": email,
        "password_hash": hash_password(DEFAULT_PASSWORD),
        "role": role,
        "created_at": now,
    }

    existing_user = await db.users.find_one({"email": email})
    if existing_user is not None:
        await db.users.update_one(
            {"_id": existing_user["_id"]},
            {
                "$set": {
                    "name": name,
                    "password_hash": payload["password_hash"],
                    "role": role,
                }
            },
        )
        return existing_user["_id"]

    result = await db.users.insert_one(payload)
    return result.inserted_id


def sample_classes(admin_id: Any) -> list[dict[str, Any]]:
    now = datetime.now(timezone.utc)
    return [
        {
            "class_name": "Lập trình Web cơ bản",
            "description": (
                "Lớp học nhập môn phát triển web với HTML, CSS, JavaScript."
            ),
            "teacher_name": "Nguyen Van B",
            "schedule": "Thứ 2, Thứ 4 - 18:00 đến 20:00",
            "room": "A101",
            "max_students": 30,
            "current_students": 0,
            "status": "open",
            "created_by": admin_id,
            "created_at": now,
            "updated_at": now,
        },
        {
            "class_name": "Cơ sở dữ liệu MongoDB",
            "description": "Lớp học cơ bản về MongoDB và thiết kế dữ liệu NoSQL.",
            "teacher_name": "Tran Thi C",
            "schedule": "Thứ 3, Thứ 5 - 18:00 đến 20:00",
            "room": "B202",
            "max_students": 25,
            "current_students": 0,
            "status": "open",
            "created_by": admin_id,
            "created_at": now,
            "updated_at": now,
        },
        {
            "class_name": "Nhập môn Python",
            "description": "Lớp học nền tảng Python cho người mới bắt đầu.",
            "teacher_name": "Le Van D",
            "schedule": "Thứ 7 - 08:00 đến 11:00",
            "room": "C303",
            "max_students": 40,
            "current_students": 0,
            "status": "open",
            "created_by": admin_id,
            "created_at": now,
            "updated_at": now,
        },
    ]


async def upsert_classes(
    db: AsyncIOMotorDatabase,
    classes: list[dict[str, Any]],
) -> None:
    for class_doc in classes:
        update_payload = {
            key: value
            for key, value in class_doc.items()
            if key != "created_at"
        }
        await db.classes.update_one(
            {"class_name": class_doc["class_name"]},
            {
                "$set": {
                    **update_payload,
                    "updated_at": datetime.now(timezone.utc),
                },
                "$setOnInsert": {"created_at": class_doc["created_at"]},
            },
            upsert=True,
        )


async def seed() -> None:
    settings = get_settings()
    client = AsyncIOMotorClient(settings.mongodb_url)
    db = client[settings.mongodb_db_name]

    try:
        await create_indexes(db)
        admin_id = await upsert_user(
            db,
            name="Admin ClassEnroll",
            email=ADMIN_EMAIL,
            role="admin",
        )
        await upsert_user(
            db,
            name="Student Demo",
            email=STUDENT_EMAIL,
            role="student",
        )
        await upsert_classes(db, sample_classes(admin_id))
        print("Seed completed successfully.")
        print(f"Admin account: {ADMIN_EMAIL} / {DEFAULT_PASSWORD}")
        print(f"Student account: {STUDENT_EMAIL} / {DEFAULT_PASSWORD}")
    finally:
        client.close()


if __name__ == "__main__":
    asyncio.run(seed())
