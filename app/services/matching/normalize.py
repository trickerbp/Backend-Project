from __future__ import annotations

import re
from typing import Any, Mapping

from app.services.matching.skill_taxonomy import (
    canonical_role,
    canonicalize_skills,
    canonicalize_topics,
    extract_skills,
    extract_topics,
    normalize_learning_format,
    normalize_level,
)


__all__ = [
    "normalize_course",
    "normalize_student_profile",
    "parse_duration_hours",
    "parse_hours_per_week",
]


_LIST_SPLIT_RE = re.compile(r"[;\n,/•·]| - | và | hoặc ", re.IGNORECASE)


def _as_list(value: Any) -> list[str]:
    """Coerce a free-form value into a list of trimmed strings.

    Accepts an existing list (already-normalized input) or a delimited string
    (raw extractor output like "React; Node.js và MySQL").
    """
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        return [str(item).strip() for item in value if str(item).strip()]
    parts = _LIST_SPLIT_RE.split(str(value))
    return [part.strip(" .;:-") for part in parts if part.strip(" .;:-")]


def _first_nonempty(source: Mapping[str, Any], *keys: str) -> str:
    for key in keys:
        value = source.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""

def _answers_text(value: Any) -> str:
    if not isinstance(value, Mapping):
        return ""
    parts: list[str] = []
    for key, answer in value.items():
        if isinstance(answer, (list, tuple, set)):
            answer_text = " ".join(str(item).strip() for item in answer if str(item).strip())
        else:
            answer_text = str(answer or "").strip()
        if answer_text:
            parts.append(f"{key}: {answer_text}")
    return " ".join(parts)

def _merge_unique(*groups: list[str]) -> list[str]:
    merged: list[str] = []
    seen: set[str] = set()
    for group in groups:
        for value in group:
            text = str(value).strip()
            key = text.casefold()
            if not text or key in seen:
                continue
            seen.add(key)
            merged.append(text)
    return merged


def parse_duration_hours(value: Any) -> int | None:
    """Pull a course duration in hours from text like '40 giờ, gồm 14 buổi'.

    Already-numeric values pass through. When the text gives only sessions
    ('14 buổi'), assume a 3-hour session as a coarse fallback.
    """
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return int(value) if value > 0 else None

    text = str(value).casefold()

    # "3 giờ/buổi, 10 buổi" = per-session rate x session count, not 3 hours
    # total. Detect the per-session pattern first so it is not mistaken for the
    # whole-course duration.
    per_session = re.search(
        r"(\d{1,2})\s*(?:gio|giờ|tiet|tiết|h)\s*/?\s*(?:buoi|buổi|session)", text
    )
    session_count = re.search(r"(\d{1,3})\s*(?:buoi|buổi|session)", text)
    if per_session and session_count:
        return int(per_session.group(1)) * int(session_count.group(1))

    hour_match = re.search(r"(\d{1,4})\s*(?:gio|giờ|tiet|tiết|hours?|h)\b", text)
    if hour_match:
        return int(hour_match.group(1))

    if session_count:
        return int(session_count.group(1)) * 3
    return None


def parse_hours_per_week(value: Any) -> int | None:
    """Estimate study hours per week from a student's free-form availability.

    Handles explicit '8 giờ/tuần', and falls back to counting weekly time
    slots ('Thứ Ba và Thứ Năm, 19:00-21:00' -> 2 slots) times a 2.5h slot.
    """
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return int(value) if value > 0 else None

    text = str(value).casefold()
    per_week = re.search(
        r"(\d{1,2})\s*(?:gio|giờ|h)\s*/?\s*(?:tuan|tuần|week)", text
    )
    if per_week:
        return int(per_week.group(1))

    day_tokens = re.findall(
        r"th[uứ]\s*(?:hai|ba|tu|tư|nam|năm|sau|sáu|bay|bảy)|ch[uủ]\s*nh[aậ]t",
        text,
    )
    if day_tokens:
        return max(1, len(set(day_tokens))) * 3
    return None


def _is_already_normalized_course(source: Mapping[str, Any]) -> bool:
    return any(
        key in source
        for key in ("course_code", "level", "extracted_skills", "manual_tags")
    )


def normalize_course(source: Mapping[str, Any]) -> dict[str, Any]:
    """Return a canonical course dict matching course_model fields.

    Works for two inputs:
      * raw extractor output (ten_khoa_hoc, noi_dung_dao_tao, ...), or
      * an already-normalized course (passed through, lists canonicalized).
    """
    title = _first_nonempty(source, "title", "ten_khoa_hoc", "course_title")
    description = _first_nonempty(
        source, "description", "noi_dung_dao_tao", "course_description"
    )
    content_text = " ".join(
        str(source.get(key, ""))
        for key in (
            "noi_dung_dao_tao",
            "description",
            "yeu_cau_dau_vao",
            "cleaned_text",
            "raw_text",
        )
    )

    if _is_already_normalized_course(source):
        level = normalize_level(source.get("level"))
        manual_tags = canonicalize_skills(_as_list(source.get("manual_tags")))
        extracted_skills = canonicalize_skills(
            _as_list(source.get("extracted_skills"))
        )
        target_goals = _as_list(source.get("target_goals"))
        topic_text = " ".join(
            str(source.get(key, ""))
            for key in (
                "title",
                "description",
                "manual_tags",
                "extracted_skills",
                "extracted_topics",
                "target_goals",
                "cleaned_text",
                "raw_text",
            )
        )
        extracted_topics = _merge_unique(
            canonicalize_topics(_as_list(source.get("extracted_topics"))),
            canonicalize_topics(_as_list(source.get("manual_tags"))),
            canonicalize_topics(target_goals),
            extract_topics(topic_text),
        )
        prerequisites = _as_list(
            source.get("extracted_prerequisites") or source.get("prerequisites")
        )
        tools = _as_list(source.get("tools"))
        duration = parse_duration_hours(source.get("duration_hours"))
    else:
        level = normalize_level(content_text) or normalize_level(title)
        manual_tags = []
        extracted_skills = canonicalize_skills(extract_skills(content_text))
        extracted_topics = canonicalize_topics(extract_topics(content_text))
        target_goals = []
        prerequisites = _as_list(source.get("yeu_cau_dau_vao"))
        tools = []
        duration = parse_duration_hours(
            _first_nonempty(source, "thoi_luong_lich_hoc")
        )

    return {
        "course_id": _first_nonempty(source, "course_id", "_id", "id") or None,
        "title": title or None,
        "course_code": _first_nonempty(source, "course_code") or None,
        "description": description or None,
        "level": level,
        "target_goals": target_goals,
        "manual_tags": manual_tags,
        "extracted_skills": extracted_skills,
        "extracted_topics": extracted_topics,
        "extracted_prerequisites": prerequisites,
        "tools": tools,
        "duration_hours": duration,
        "behavior_score": source.get("behavior_score"),
        # Combined free text used for the text-similarity dimension.
        "content_text": " ".join(
            part for part in (title, description, content_text) if part
        ).strip(),
    }


def _is_already_normalized_profile(source: Mapping[str, Any]) -> bool:
    return any(
        key in source
        for key in (
            "career_goal",
            "current_skills",
            "desired_skills",
            "current_level",
            "intent_text",
        )
    )


def normalize_student_profile(source: Mapping[str, Any]) -> dict[str, Any]:
    """Return a canonical student profile matching student_profile_model.

    Accepts raw extractor output (kien_thuc_nen_tang, muc_tieu_hoc_tap, ...)
    or an already-normalized profile.
    """
    if _is_already_normalized_profile(source):
        career_goal = _first_nonempty(source, "career_goal")
        current_level = normalize_level(source.get("current_level"))
        current_skills = canonicalize_skills(_as_list(source.get("current_skills")))
        intent_text = _first_nonempty(source, "intent_text")
        answers_text = _answers_text(source.get("question_answers"))
        background_text = " ".join(
            part
            for part in (
                intent_text,
                answers_text,
                _first_nonempty(source, "cleaned_text", "raw_text"),
            )
            if part
        )
        explicit_desired = canonicalize_skills(_as_list(source.get("desired_skills")))
        desired_skills = explicit_desired or canonicalize_skills(
            extract_skills(f"{intent_text} {answers_text}")
        )
        explicit_topics = canonicalize_topics(_as_list(source.get("interested_topics")))
        interested = explicit_topics or canonicalize_topics(
            extract_topics(f"{intent_text} {answers_text}")
        )
        hours = parse_hours_per_week(source.get("hours_per_week"))
        learning_format = normalize_learning_format(
            source.get("learning_format")
        )
        goal_text = career_goal
        if not career_goal:
            career_goal = canonical_role(background_text) or ""
    else:
        background = _first_nonempty(source, "kien_thuc_nen_tang")
        goal_text = _first_nonempty(source, "muc_tieu_hoc_tap")
        current_level = normalize_level(background)
        current_skills = canonicalize_skills(extract_skills(background))
        # Desired skills come from the goal statement; remove anything the
        # student already has so the gap is honest.
        desired_raw = canonicalize_skills(extract_skills(goal_text))
        owned = {skill.casefold() for skill in current_skills}
        desired_skills = [s for s in desired_raw if s.casefold() not in owned]
        interested = canonicalize_topics(
            extract_topics(f"{goal_text} {background}")
        )
        hours = parse_hours_per_week(_first_nonempty(source, "thoi_gian_hoc"))
        learning_format = normalize_learning_format(
            _first_nonempty(source, "hinh_thuc_hoc")
        )
        # Recover a career goal from the objective text when possible, so the
        # goal dimension is not dead for file-sourced profiles.
        career_goal = canonical_role(goal_text) or ""
        background_text = background

    return {
        "student_id": _first_nonempty(source, "student_id", "_id", "id") or None,
        "source_type": _first_nonempty(source, "source_type") or "uploaded_file",
        "intent_text": _first_nonempty(source, "intent_text") or None,
        "question_answers": source.get("question_answers") or {},
        "career_goal": career_goal or None,
        "current_level": current_level,
        "current_skills": current_skills,
        "desired_skills": desired_skills,
        "interested_topics": interested,
        "hours_per_week": hours,
        "learning_format": learning_format,
        "content_text": " ".join(
            part for part in (goal_text, background_text) if part
        ).strip(),
    }
