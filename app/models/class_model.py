from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from bson import ObjectId


CLASSES_COLLECTION = "classes"


def create_class_document(
    class_data: dict[str, Any],
    created_by: ObjectId,
) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    return {
        **class_data,
        "current_students": class_data.get("current_students", 0),
        "created_by": created_by,
        "created_at": now,
        "updated_at": now,
    }


def class_to_response(class_doc: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(class_doc["_id"]),
        "class_name": class_doc["class_name"],
        "description": class_doc["description"],
        "teacher_name": class_doc["teacher_name"],
        "schedule": class_doc["schedule"],
        "room": class_doc["room"],
        "max_students": class_doc["max_students"],
        "current_students": class_doc.get("current_students", 0),
        "status": class_doc["status"],
        "created_by": str(class_doc["created_by"]),
        "created_at": class_doc["created_at"],
        "updated_at": class_doc.get("updated_at"),
    }
