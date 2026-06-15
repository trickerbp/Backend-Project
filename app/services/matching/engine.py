from __future__ import annotations

from typing import Any, Mapping, Sequence

from app.services.matching.normalize import (
    normalize_course,
    normalize_student_profile,
)
from app.services.matching.scoring import (
    CourseMatch,
    ScoreWeights,
    score_course_for_student,
)


__all__ = [
    "rank_courses_for_student",
    "match_student_to_courses",
]


def rank_courses_for_student(
    normalized_profile: Mapping[str, Any],
    normalized_courses: Sequence[Mapping[str, Any]],
    *,
    weights: ScoreWeights | None = None,
    min_score: float = 0.0,
    top_k: int | None = None,
) -> list[CourseMatch]:
    """Score every course for one already-normalized profile and rank them.

    Courses scoring at or below ``min_score`` are dropped. Ties are broken by
    course_code then title so the order is stable across runs.
    """
    matches = [
        score_course_for_student(normalized_profile, course, weights)
        for course in normalized_courses
    ]
    matches = [match for match in matches if match.score > min_score]
    matches.sort(
        key=lambda m: (
            -m.score,
            (m.course_code or ""),
            (m.title or ""),
        )
    )
    if top_k is not None:
        matches = matches[:top_k]
    return matches


def match_student_to_courses(
    profile_source: Mapping[str, Any],
    course_sources: Sequence[Mapping[str, Any]],
    *,
    weights: ScoreWeights | None = None,
    min_score: float = 0.0,
    top_k: int | None = None,
) -> dict[str, Any]:
    """End-to-end for one student: normalize inputs, rank, return a plain dict.

    Accepts raw extractor output or already-normalized dicts on both sides
    (normalize.py handles either). Returns a JSON-serializable result.
    """
    normalized_profile = normalize_student_profile(profile_source)
    normalized_courses = [normalize_course(course) for course in course_sources]
    matches = rank_courses_for_student(
        normalized_profile,
        normalized_courses,
        weights=weights,
        min_score=min_score,
        top_k=top_k,
    )
    return {
        "student_id": normalized_profile.get("student_id"),
        "profile": {
            "career_goal": normalized_profile.get("career_goal"),
            "current_level": normalized_profile.get("current_level"),
            "current_skills": normalized_profile.get("current_skills"),
            "desired_skills": normalized_profile.get("desired_skills"),
            "interested_topics": normalized_profile.get("interested_topics"),
            "hours_per_week": normalized_profile.get("hours_per_week"),
            "learning_format": normalized_profile.get("learning_format"),
        },
        "recommendations": [match.to_dict() for match in matches],
    }
