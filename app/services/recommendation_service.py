from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.recommendation_model import RECOMMENDATIONS_COLLECTION
from app.services.matching.normalize import (
    normalize_course,
    normalize_student_profile,
)
from app.services.matching.scoring import score_course_for_student
from app.services.processing_log_service import write_processing_log


def _score_course(
    profile: dict[str, Any],
    course: dict[str, Any],
) -> dict[str, Any] | None:
    """Score one course for one student using the shared matching core.

    Returns the stored-result dict, or None when the course scores nothing so
    it is dropped from the recommendation list. The raw Mongo ObjectId is kept
    on ``course_id`` for downstream resource lookup; it is stringified later by
    ``recommendation_to_public``.
    """
    normalized_profile = normalize_student_profile(profile)
    normalized_course = normalize_course(course)
    match = score_course_for_student(normalized_profile, normalized_course)
    if match.score <= 0:
        return None

    stored = match.to_dict()
    # Preserve the real ObjectId for resource lookup; normalize_course only
    # carries a stringified id.
    stored["course_id"] = course["_id"]
    stored["matched_resource_ids"] = []
    return stored


async def _resource_ids_for_course(
    db: AsyncIOMotorDatabase,
    course_id: ObjectId,
    matched_skills: list[str],
) -> list[ObjectId]:
    if not matched_skills:
        return []
    skill_regexes = [
        {"extracted_skills": {"$regex": f"^{skill}$", "$options": "i"}}
        for skill in matched_skills
    ]
    cursor = db.course_resources.find(
        {"course_id": course_id, "$or": skill_regexes},
        {"_id": 1},
    )
    docs = await cursor.to_list(length=None)
    return [doc["_id"] for doc in docs]


async def generate_recommendations(
    db: AsyncIOMotorDatabase,
    student_id: ObjectId,
    profile: dict[str, Any],
) -> dict[str, Any]:
    courses = await db.courses.find({"status": "active"}).to_list(length=None)

    results: list[dict[str, Any]] = []
    for course in courses:
        scored = _score_course(profile, course)
        if scored is None:
            continue
        scored["matched_resource_ids"] = await _resource_ids_for_course(
            db, course["_id"], scored["matched_skills"]
        )
        results.append(scored)

    results.sort(key=lambda item: item["score"], reverse=True)

    document = {
        "student_id": student_id,
        "student_profile_id": profile["_id"],
        "results": results,
        "created_at": datetime.now(timezone.utc),
    }
    insert_result = await db[RECOMMENDATIONS_COLLECTION].insert_one(document)
    document["_id"] = insert_result.inserted_id
    await write_processing_log(
        db,
        None,
        None,
        "generate_recommendation",
        "success",
        f"Generated {len(results)} recommendations.",
    )
    return document
