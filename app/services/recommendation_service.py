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
from app.services.matching.text_similarity import text_similarity
from app.services.processing_log_service import write_processing_log

EVENT_WEIGHTS = {
    "view": 0.35,
    "select": 1.0,
    "save": 0.8,
    "dismiss": -0.5,
}

def _score_course(
    normalized_profile: dict[str, Any],
    course: dict[str, Any],
) -> dict[str, Any] | None:
    """Score one course for one student using the shared matching core.

    Returns the stored-result dict, or None when the course scores nothing so
    it is dropped from the recommendation list. The raw Mongo ObjectId is kept
    on ``course_id`` for downstream resource lookup; it is stringified later by
    ``recommendation_to_public``.
    """
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


def _list(value: Any) -> list[str]:
    if isinstance(value, (list, tuple, set)):
        return [str(item).strip() for item in value if str(item).strip()]
    if value is None:
        return []
    text = str(value).strip()
    return [text] if text else []


def _jaccard(left: list[str], right: list[str]) -> float:
    left_set = {item.casefold() for item in left}
    right_set = {item.casefold() for item in right}
    if not left_set or not right_set:
        return 0.0
    return len(left_set & right_set) / len(left_set | right_set)


def _course_similarity(left: dict[str, Any], right: dict[str, Any]) -> float:
    left_norm = normalize_course(left)
    right_norm = normalize_course(right)
    skill_overlap = _jaccard(
        _list(left_norm.get("extracted_skills")) + _list(left_norm.get("manual_tags")),
        _list(right_norm.get("extracted_skills")) + _list(right_norm.get("manual_tags")),
    )
    topic_overlap = _jaccard(
        _list(left_norm.get("extracted_topics")),
        _list(right_norm.get("extracted_topics")),
    )
    text_overlap = text_similarity(
        str(left_norm.get("content_text") or ""),
        str(right_norm.get("content_text") or ""),
    )
    return max(skill_overlap, topic_overlap, text_overlap)


async def _behavior_scores(
    db: AsyncIOMotorDatabase,
    student_id: ObjectId,
    courses: list[dict[str, Any]],
) -> dict[ObjectId, float]:
    events = (
        await db.recommendation_events.find({"student_id": student_id})
        .sort("created_at", -1)
        .to_list(length=80)
    )
    if not events:
        return {}

    event_course_ids = [
        event.get("course_id")
        for event in events
        if isinstance(event.get("course_id"), ObjectId)
    ]
    if not event_course_ids:
        return {}

    event_courses = {
        doc["_id"]: doc
        for doc in await db.courses.find({"_id": {"$in": event_course_ids}}).to_list(length=None)
    }
    scores: dict[ObjectId, float] = {}
    for course in courses:
        best = 0.0
        for event in events:
            event_course = event_courses.get(event.get("course_id"))
            if event_course is None:
                continue
            event_weight = EVENT_WEIGHTS.get(str(event.get("event_type")), 0.0)
            if event_weight <= 0:
                continue
            if course["_id"] == event_course["_id"]:
                signal = 1.0
            else:
                signal = _course_similarity(course, event_course)
            best = max(best, event_weight * signal)
        if best > 0:
            scores[course["_id"]] = min(1.0, best)
    return scores


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
    normalized_profile = normalize_student_profile(profile)
    behavior_scores = await _behavior_scores(db, student_id, courses)

    results: list[dict[str, Any]] = []
    for course in courses:
        course_with_behavior = {
            **course,
            "behavior_score": behavior_scores.get(course["_id"]),
        }
        scored = _score_course(normalized_profile, course_with_behavior)
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
