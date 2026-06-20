from __future__ import annotations

import re
import unicodedata
from typing import Any

from app.core.config import get_settings
from app.services import azure_document_ocr_service
from app.services import text_cleaning_service as cleaner
from app.services.matching.core_engine import core_extractor
from app.services.matching.normalize import parse_hours_per_week
from app.services.matching.skill_taxonomy import (
    canonical_role,
    extract_skills,
    extract_topics,
    normalize_learning_format,
    normalize_level,
)


def _parse_with_optional_ocr(file_path: str, file_type: str) -> tuple[str, str | None]:
    raw_text = core_extractor.parse_document(file_path, file_type)
    settings = get_settings()
    if (
        settings.use_azure_document_intelligence
        and file_type in {"pdf", "docx", "pptx"}
        and len(raw_text.strip()) < settings.ocr_min_text_chars
    ):
        ocr_text = azure_document_ocr_service.extract_text(file_path)
        if len(ocr_text.strip()) > len(raw_text.strip()):
            return ocr_text, "azure_document_intelligence"
    return raw_text, None


def _ascii_fold(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value.casefold())
    without_marks = "".join(char for char in decomposed if not unicodedata.combining(char))
    return re.sub(r"\s+", " ", without_marks).strip()


def _first_meaningful_line(text: str) -> str:
    for raw_line in text.splitlines():
        line = re.sub(r"^\s{0,3}#{1,6}\s+", "", raw_line)
        line = re.sub(r"^[\s*\-\u2022]+", "", line).strip()
        if 4 <= len(line) <= 160:
            return line
    return ""


def _excerpt(text: str, max_length: int = 800) -> str:
    compact = re.sub(r"\s+", " ", text).strip()
    return compact[:max_length]


def _section_after(text: str, markers: tuple[str, ...]) -> str:
    capture: list[str] = []
    capturing = False
    for raw_line in text.splitlines():
        line = raw_line.strip()
        normalized = _ascii_fold(line)
        if not capturing and any(marker in normalized for marker in markers):
            capturing = True
            capture.append(line)
            continue
        if capturing:
            if not line:
                break
            if len(capture) >= 8:
                break
            capture.append(line)
    return "\n".join(capture)


def preview_course_from_file(file_path: str, file_type: str) -> dict[str, Any]:
    raw_text, ocr_provider = _parse_with_optional_ocr(file_path, file_type)
    cleaned_text = cleaner.clean_text(raw_text)
    info = core_extractor.extract_course_info(cleaned_text)
    title = info.get("extracted_title") or _first_meaningful_line(cleaned_text)
    description = info.get("summary") or info.get("extracted_description") or _excerpt(cleaned_text)

    return {
        "title": title,
        "course_code": "",
        "description": description,
        "level": info.get("extracted_level") or "beginner",
        "target_goals": info.get("extracted_objectives", []),
        "manual_tags": info.get("extracted_skills", []),
        "tools": info.get("extracted_tools", []),
        "duration_hours": info.get("extracted_duration_hours"),
        "status": "draft",
        "extracted_skills": info.get("extracted_skills", []),
        "extracted_topics": info.get("extracted_topics", []),
        "extracted_objectives": info.get("extracted_objectives", []),
        "extracted_prerequisites": info.get("extracted_prerequisites", []),
        "summary": info.get("summary"),
        "raw_text_length": len(raw_text),
        "cleaned_text_length": len(cleaned_text),
        "ocr_provider": ocr_provider,
    }


def preview_student_profile_from_file(file_path: str, file_type: str) -> dict[str, Any]:
    raw_text, ocr_provider = _parse_with_optional_ocr(file_path, file_type)
    cleaned_text = cleaner.clean_text(raw_text)
    goal_text = _section_after(
        cleaned_text,
        ("muc tieu", "career", "objective", "mong muon"),
    )
    current_text = _section_after(
        cleaned_text,
        ("ky nang hien", "kinh nghiem", "background", "experience"),
    )
    desired_text = _section_after(
        cleaned_text,
        ("muon hoc", "can hoc", "desired", "interested"),
    )

    current_skills = extract_skills(current_text or cleaned_text)
    desired_skills = extract_skills(desired_text or goal_text)
    owned = {skill.casefold() for skill in current_skills}
    desired_skills = [skill for skill in desired_skills if skill.casefold() not in owned]
    career_goal = canonical_role(goal_text or cleaned_text) or _first_meaningful_line(goal_text)

    return {
        "source_type": "uploaded_file",
        "career_goal": career_goal,
        "current_level": normalize_level(cleaned_text) or "beginner",
        "current_skills": current_skills,
        "desired_skills": desired_skills,
        "interested_topics": extract_topics("\n".join([goal_text, desired_text, cleaned_text])),
        "hours_per_week": parse_hours_per_week(cleaned_text),
        "learning_format": normalize_learning_format(cleaned_text) or "online",
        "raw_text_length": len(raw_text),
        "cleaned_text_length": len(cleaned_text),
        "ocr_provider": ocr_provider,
    }
