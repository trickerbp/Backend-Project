from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from bson import ObjectId


PROCESSING_LOGS_COLLECTION = "processing_logs"


def create_log_document(
    resource_id: ObjectId | None,
    course_id: ObjectId | None,
    step: str,
    status: str,
    message: str,
) -> dict[str, Any]:
    return {
        "resource_id": resource_id,
        "course_id": course_id,
        "step": step,
        "status": status,
        "message": message,
        "created_at": datetime.now(timezone.utc),
    }


def log_to_public(log: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(log["_id"]),
        "resource_id": str(log["resource_id"]) if log.get("resource_id") else None,
        "course_id": str(log["course_id"]) if log.get("course_id") else None,
        "step": log.get("step"),
        "status": log.get("status"),
        "message": log.get("message"),
        "created_at": log.get("created_at"),
    }
