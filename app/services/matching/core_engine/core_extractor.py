from __future__ import annotations

# Backend-facing adapter over the vendored Core Engine.
#
# Replaces the two extraction steps in course_resource_service with the richer
# Core Engine parser (OCR + tables + layout-aware markdown) and the shared
# matching taxonomy (50+ skill/topic aliases) instead of a 28-item keyword list.
#
# Two drop-in functions mirror the originals so the service wiring stays small:
#   * parse_document(file_path, file_type) -> str   (was extract_text_by_file_type)
#   * extract_course_info(cleaned_text)    -> dict   (same keys as before)

import os
import re
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


# Tools are not part of the skill/topic taxonomy, so keep a small dedicated list.
# Matched on diacritic-stripped, spaced-lowercase text (see normalize_text).
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
        )
    )


def parse_document(file_path: str, file_type: str) -> str:
    """Return rich text for one resource file.

    PDF and DOCX go through the Core Engine parser (OCR, tables, layout-aware
    markdown). PPTX still uses python-pptx text extraction because the Core
    Engine converts slides via LibreOffice, which the backend does not require.
    OCR auto-disables inside the parser when Tesseract/Pillow are unavailable.
    """
    if file_type == "pptx":
        # Leaf module, no app-internal deps -> safe import, no cycle.
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
                r"(?<![a-z0-9+#.])" + re.escape(normalize_text(alias)) + r"(?![a-z0-9+#.])"
            )
            if re.search(pattern, normalized_text):
                found.append(canonical)
                break
    return found


def _extract_section_items(text: str, headers: tuple[str, ...]) -> list[str]:
    """Capture list-like lines following a known section header.

    Stops at the first blank line after the header. Works on the cleaned
    markdown: header lines may carry '#'/'-' markdown which is stripped before
    matching.
    """
    items: list[str] = []
    capturing = False
    for raw_line in text.splitlines():
        stripped = raw_line.strip()
        bare = re.sub(r"^\s{0,3}#{1,6}\s+", "", stripped)
        normalized = normalize_text(bare)
        if not capturing:
            if normalized and any(normalized.startswith(h) for h in headers):
                capturing = True
            continue
        if not stripped:
            break
        if re.match(r"^\s{0,3}#{1,6}\s+", raw_line):
            break  # next heading ends the section
        item = re.sub(r"^[\-*•\d.)\s]+", "", stripped).strip()
        if item and len(item) < 200:
            items.append(item)
    return items[:20]


def extract_course_info(cleaned_text: str) -> dict[str, Any]:
    """Drop-in replacement for course_resource_service.extract_course_info.

    Same output keys, but skills/topics come from the shared taxonomy and the
    input is the richer Core Engine markdown rather than flat page text.
    """
    normalized = normalize_text(cleaned_text)
    first_line = (
        cleaned_text.strip().splitlines()[0][:300] if cleaned_text.strip() else None
    )
    # Strip a leading markdown heading marker from the summary line.
    summary = (
        re.sub(r"^\s{0,3}#{1,6}\s+", "", first_line).strip() if first_line else None
    )

    return {
        "extracted_title": None,
        "extracted_description": summary,
        "extracted_level": normalize_level(normalized),
        "extracted_skills": extract_skills(cleaned_text),
        "extracted_topics": extract_topics(cleaned_text),
        "extracted_objectives": _extract_section_items(
            cleaned_text, _OBJECTIVE_HEADERS
        ),
        "extracted_prerequisites": _extract_section_items(
            cleaned_text, _PREREQUISITE_HEADERS
        ),
        "extracted_tools": _extract_tools(normalized),
        "extracted_duration_hours": parse_duration_hours(cleaned_text),
        "summary": summary,
    }
