from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from bson import ObjectId


ENROLLMENTS_COLLECTION = "enrollments"


def create_enrollment_document(
    student_id: ObjectId,
    class_id: ObjectId,
    note: str | None = None,
) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    return {
        "student_id": student_id,
        "class_id": class_id,
        "status": "pending",
        "note": note,
        "created_at": now,
        "updated_at": now,
        "approved_by": None,
    }


def enrollment_to_response(enrollment: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(enrollment["_id"]),
        "student_id": str(enrollment["student_id"]),
        "class_id": str(enrollment["class_id"]),
        "status": enrollment["status"],
        "note": enrollment.get("note"),
        "created_at": enrollment["created_at"],
        "updated_at": enrollment.get("updated_at"),
        "approved_by": (
            str(enrollment["approved_by"])
            if enrollment.get("approved_by") is not None
            else None
        ),
    }
