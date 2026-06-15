from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from bson import ObjectId


COURSES_COLLECTION = "courses"

VALID_LEVELS = {"beginner", "intermediate", "advanced"}
VALID_STATUSES = {"draft", "active", "archived"}


def create_course_document(
    title: str,
    course_code: str,
    description: str,
    level: str,
    teacher_id: ObjectId,
    target_goals: list[str] | None = None,
    manual_tags: list[str] | None = None,
    tools: list[str] | None = None,
    duration_hours: int | None = None,
    status: str = "draft",
) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    return {
        "title": title,
        "course_code": course_code,
        "description": description,
        "level": level,
        "target_goals": target_goals or [],
        "manual_tags": manual_tags or [],
        "extracted_skills": [],
        "extracted_topics": [],
        "extracted_objectives": [],
        "extracted_prerequisites": [],
        "tools": tools or [],
        "duration_hours": duration_hours,
        "teacher_id": teacher_id,
        "status": status,
        "created_at": now,
        "updated_at": now,
    }


def course_to_public(course: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(course["_id"]),
        "title": course.get("title"),
        "course_code": course.get("course_code"),
        "description": course.get("description"),
        "level": course.get("level"),
        "target_goals": course.get("target_goals", []),
        "manual_tags": course.get("manual_tags", []),
        "extracted_skills": course.get("extracted_skills", []),
        "extracted_topics": course.get("extracted_topics", []),
        "extracted_objectives": course.get("extracted_objectives", []),
        "extracted_prerequisites": course.get("extracted_prerequisites", []),
        "tools": course.get("tools", []),
        "duration_hours": course.get("duration_hours"),
        "teacher_id": str(course["teacher_id"]) if course.get("teacher_id") else None,
        "status": course.get("status"),
        "created_at": course.get("created_at"),
        "updated_at": course.get("updated_at"),
    }
