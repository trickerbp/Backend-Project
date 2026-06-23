from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from bson import ObjectId


STUDENT_PROFILES_COLLECTION = "student_profiles"

VALID_SOURCE_TYPES = {"manual_form", "uploaded_file"}
VALID_LEVELS = {"beginner", "intermediate", "advanced"}
VALID_LEARNING_FORMATS = {"online", "offline", "hybrid"}


def create_profile_document(
    student_id: ObjectId,
    source_type: str,
    career_goal: str = "",
    current_level: str | None = None,
    current_skills: list[str] | None = None,
    desired_skills: list[str] | None = None,
    interested_topics: list[str] | None = None,
    hours_per_week: int | None = None,
    learning_format: str | None = None,
    intent_text: str | None = None,
    question_answers: dict[str, Any] | None = None,
    uploaded_file_name: str | None = None,
    file_path: str | None = None,
    raw_text: str | None = None,
    cleaned_text: str | None = None,
) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    return {
        "student_id": student_id,
        "source_type": source_type,
        "intent_text": intent_text or "",
        "question_answers": question_answers or {},
        "career_goal": career_goal,
        "current_level": current_level,
        "current_skills": current_skills or [],
        "desired_skills": desired_skills or [],
        "interested_topics": interested_topics or [],
        "hours_per_week": hours_per_week,
        "learning_format": learning_format,
        "uploaded_file_name": uploaded_file_name,
        "file_path": file_path,
        "raw_text": raw_text,
        "cleaned_text": cleaned_text,
        "created_at": now,
        "updated_at": now,
    }


def profile_to_public(profile: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(profile["_id"]),
        "student_id": str(profile["student_id"]),
        "source_type": profile.get("source_type"),
        "intent_text": profile.get("intent_text"),
        "question_answers": profile.get("question_answers", {}),
        "career_goal": profile.get("career_goal"),
        "current_level": profile.get("current_level"),
        "current_skills": profile.get("current_skills", []),
        "desired_skills": profile.get("desired_skills", []),
        "interested_topics": profile.get("interested_topics", []),
        "hours_per_week": profile.get("hours_per_week"),
        "learning_format": profile.get("learning_format"),
        "uploaded_file_name": profile.get("uploaded_file_name"),
        "file_path": profile.get("file_path"),
        "raw_text": profile.get("raw_text"),
        "cleaned_text": profile.get("cleaned_text"),
        "created_at": profile.get("created_at"),
        "updated_at": profile.get("updated_at"),
    }
