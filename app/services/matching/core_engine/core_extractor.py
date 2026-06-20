from __future__ import annotations

import os
import re
import unicodedata
from pathlib import Path
from typing import Any

from app.services.matching.core_engine.document_processing_model import (
    DocumentParser,
    ParserConfig,
)
from app.services.matching.normalize import parse_duration_hours
from app.services.matching.skill_taxonomy import (
    extract_skills,
    extract_topics,
    normalize_level,
    normalize_text,
)

__all__ = ["parse_document", "extract_course_info"]

_TOOL_KEYWORDS: dict[str, tuple[str, ...]] = {
    "VS Code": ("vs code", "visual studio code", "vscode"),
    "Git": ("git",),
    "GitHub": ("github",),
    "GitLab": ("gitlab",),
    "Chrome DevTools": ("chrome devtools", "devtools"),
    "MongoDB Compass": ("mongodb compass", "compass"),
    "mongosh": ("mongosh",),
    "MongoDB Atlas": ("mongodb atlas", "atlas"),
    "Jupyter Notebook": ("jupyter notebook", "jupyter"),
    "DBeaver": ("dbeaver",),
    "MySQL Workbench": ("mysql workbench",),
    "Docker": ("docker",),
    "Postman": ("postman",),
    "Figma": ("figma",),
}

_OBJECTIVE_HEADERS = (
    "muc tieu",
    "sau khoa hoc",
    "hoc vien co the",
    "sinh vien co the",
    "chuan dau ra",
    "ket qua hoc tap",
    "objective",
    "learning outcome",
)
_PREREQUISITE_HEADERS = (
    "dieu kien tien quyet",
    "yeu cau dau vao",
    "kien thuc tien quyet",
    "can biet",
    "tien quyet",
    "prerequisite",
)
_TITLE_LABELS = (
    "ten khoa hoc",
    "ten hoc phan",
    "ten mon hoc",
    "course name",
    "course title",
)
_CODE_LABELS = (
    "ma khoa hoc",
    "ma hoc phan",
    "ma mon hoc",
    "course code",
)
_DESCRIPTION_LABELS = (
    "mo ta khoa hoc",
    "tong quan khoa hoc",
    "doi tuong hoc vien phu hop",
    "noi dung khoa hoc",
    "course description",
)
_LEVEL_LABELS = (
    "trinh do phu hop",
    "trinh do",
    "cap do",
    "level",
)
_DURATION_LABELS = (
    "thoi luong khoa hoc",
    "thoi luong",
    "so gio",
    "duration",
)
_TARGET_GOAL_LABELS = (
    "muc tieu nghe nghiep lien quan",
    "muc tieu nghe nghiep",
    "nghe nghiep lien quan",
    "career goals",
    "career goal",
)
_SKILL_LABELS = (
    "tu khoa ky nang chinh",
    "ky nang chinh",
    "ky nang",
    "skills",
)
_TOOLS_LABELS = (
    "cong cu phan mem su dung",
    "cong cu su dung",
    "phan mem su dung",
    "tools",
)


def _env_flag(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().casefold() in {"1", "true", "yes", "on"}


def _build_parser() -> DocumentParser:
    return DocumentParser(
        ParserConfig(
            enable_ocr=_env_flag("ENABLE_OCR", True),
            ocr_language=os.getenv("OCR_LANGUAGE", "vie+eng"),
            tesseract_cmd=os.getenv("TESSERACT_CMD") or None,
            include_document_title=False,
        )
    )


def parse_document(file_path: str, file_type: str) -> str:
    if file_type == "pptx":
        from app.services.file_extraction_service import extract_text_from_pptx

        return extract_text_from_pptx(file_path)

    if file_type in {"pdf", "docx"}:
        return _build_parser().parse(Path(file_path))

    raise ValueError(f"Unsupported file type: {file_type}")


def _extract_tools(normalized_text: str) -> list[str]:
    found: list[str] = []
    for canonical, aliases in _TOOL_KEYWORDS.items():
        for alias in aliases:
            pattern = (
                r"(?<![a-z0-9+#.])"
                + re.escape(normalize_text(alias))
                + r"(?![a-z0-9+#.])"
            )
            if re.search(pattern, normalized_text):
                found.append(canonical)
                break
    return found


def _match_text(value: object) -> str:
    decomposed = unicodedata.normalize("NFD", str(value or "").casefold())
    without_marks = "".join(
        character
        for character in decomposed
        if unicodedata.category(character) != "Mn"
    ).replace("\u0111", "d")
    return re.sub(r"[^a-z0-9+#.]+", " ", without_marks).strip()


def _strip_line_prefix(line: str) -> str:
    stripped = re.sub(r"^\s{0,3}#{1,6}\s+", "", line.strip())
    stripped = re.sub(r"^\s*(?:[-+*\u2022]|\d+[.)])\s+", "", stripped)
    return stripped.strip()


def _extract_labeled_value(text: str, labels: tuple[str, ...]) -> str:
    normalized_labels = {_match_text(label) for label in labels}
    for raw_line in text.splitlines():
        line = _strip_line_prefix(raw_line)
        match = re.match(r"^(.{1,90}?)[:]\s*(.+)$", line)
        if not match:
            continue
        label = _match_text(match.group(1))
        if label in normalized_labels:
            return match.group(2).strip(" .;:-")
    return ""


def _split_labeled_list(value: str) -> list[str]:
    if not value:
        return []
    value = re.sub(
        r"\s+(?:and|or|va|hoac|v\u00e0|ho\u1eb7c)\s+",
        ", ",
        value,
        flags=re.IGNORECASE,
    )
    pieces = re.split(r"[;,\n]+", value)
    return [piece.strip(" .;:-") for piece in pieces if piece.strip(" .;:-")]


def _merge_unique(*groups: list[str]) -> list[str]:
    merged: list[str] = []
    seen: set[str] = set()
    for group in groups:
        for item in group:
            key = _match_text(item)
            if not key or key in seen:
                continue
            seen.add(key)
            merged.append(item)
    return merged


def _extract_section_items(text: str, headers: tuple[str, ...]) -> list[str]:
    items: list[str] = []
    capturing = False
    for raw_line in text.splitlines():
        stripped = raw_line.strip()
        bare = _strip_line_prefix(stripped)
        normalized = _match_text(bare)
        if not capturing:
            if normalized and any(normalized.startswith(header) for header in headers):
                inline = _extract_labeled_value(stripped, headers)
                if inline:
                    items.extend(_split_labeled_list(inline))
                    continue
                if ":" in stripped:
                    items.extend(_split_labeled_list(stripped.split(":", 1)[1]))
                    continue
                capturing = True
            continue
        if not stripped:
            break
        if re.match(r"^\s{0,3}#{1,6}\s+", raw_line):
            break
        item = _strip_line_prefix(stripped)
        if item and len(item) < 200:
            items.append(item)
    return items[:20]


def extract_course_info(cleaned_text: str) -> dict[str, Any]:
    normalized = normalize_text(cleaned_text)
    first_line = (
        cleaned_text.strip().splitlines()[0][:300] if cleaned_text.strip() else None
    )
    summary = (
        re.sub(r"^\s{0,3}#{1,6}\s+", "", first_line).strip() if first_line else None
    )
    title = _extract_labeled_value(cleaned_text, _TITLE_LABELS)
    course_code = _extract_labeled_value(cleaned_text, _CODE_LABELS)
    description = _extract_labeled_value(cleaned_text, _DESCRIPTION_LABELS) or summary
    level_text = _extract_labeled_value(cleaned_text, _LEVEL_LABELS)
    duration_text = _extract_labeled_value(cleaned_text, _DURATION_LABELS)
    labeled_goals = _split_labeled_list(
        _extract_labeled_value(cleaned_text, _TARGET_GOAL_LABELS)
    )
    labeled_skills = _split_labeled_list(
        _extract_labeled_value(cleaned_text, _SKILL_LABELS)
    )
    labeled_tools = _split_labeled_list(
        _extract_labeled_value(cleaned_text, _TOOLS_LABELS)
    )
    objectives = _merge_unique(
        labeled_goals,
        _extract_section_items(cleaned_text, _OBJECTIVE_HEADERS),
    )
    prerequisites = _merge_unique(
        _split_labeled_list(_extract_labeled_value(cleaned_text, _PREREQUISITE_HEADERS)),
        _extract_section_items(cleaned_text, _PREREQUISITE_HEADERS),
    )

    return {
        "extracted_title": title or None,
        "course_code": course_code,
        "extracted_description": description,
        "extracted_level": normalize_level(level_text) or normalize_level(normalized),
        "extracted_skills": _merge_unique(extract_skills(cleaned_text), labeled_skills),
        "extracted_topics": extract_topics(cleaned_text),
        "extracted_objectives": objectives,
        "extracted_prerequisites": prerequisites,
        "extracted_tools": _merge_unique(_extract_tools(normalized), labeled_tools),
        "extracted_duration_hours": parse_duration_hours(duration_text)
        or parse_duration_hours(cleaned_text),
        "summary": summary,
    }
