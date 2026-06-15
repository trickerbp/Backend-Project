from __future__ import annotations

import re
import unicodedata
from typing import Iterable


__all__ = [
    "canonical_skill",
    "canonical_topic",
    "canonical_role",
    "extract_skills",
    "extract_topics",
    "canonicalize_skills",
    "canonicalize_topics",
    "normalize_text",
    "normalize_level",
    "normalize_learning_format",
    "SKILL_ALIASES",
    "TOPIC_ALIASES",
    "ROLE_ALIASES",
    "VALID_LEVELS",
    "VALID_LEARNING_FORMATS",
]


VALID_LEVELS = ("beginner", "intermediate", "advanced")
VALID_LEARNING_FORMATS = ("online", "offline", "hybrid")


def normalize_text(value: object) -> str:
    """Casefold, strip Vietnamese diacritics, collapse to spaced lowercase."""
    decomposed = unicodedata.normalize("NFD", str(value or "").casefold())
    without_marks = "".join(
        character
        for character in decomposed
        if unicodedata.category(character) != "Mn"
    ).replace("đ", "d")
    return re.sub(r"[^a-z0-9+#.]+", " ", without_marks).strip()


# Canonical skill label -> list of alias surface forms (matched after
# normalize_text, so diacritics/case are irrelevant). The first alias is
# treated as the human-facing display value.
SKILL_ALIASES: dict[str, tuple[str, ...]] = {
    "HTML": ("html",),
    "CSS": ("css",),
    "JavaScript": ("javascript", "js"),
    "TypeScript": ("typescript", "ts"),
    "React": ("react", "reactjs", "react.js"),
    "Node.js": ("node.js", "nodejs", "node js", "node"),
    "Express": ("express", "expressjs", "express.js"),
    "DOM": ("dom",),
    "Responsive Design": ("responsive design", "responsive"),
    "Python": ("python",),
    "FastAPI": ("fastapi", "fast api"),
    "Flask": ("flask",),
    "Django": ("django",),
    "REST API": ("rest api", "restful api", "restful", "rest"),
    "API": ("api",),
    "JWT": ("jwt", "json web token"),
    "OOP": ("oop", "object oriented", "huong doi tuong", "lap trinh huong doi tuong"),
    "SQL": ("sql",),
    "NoSQL": ("nosql",),
    "MongoDB": ("mongodb", "mongo"),
    "PostgreSQL": ("postgresql", "postgres"),
    "MySQL": ("mysql",),
    "Redis": ("redis",),
    "Docker": ("docker",),
    "Kubernetes": ("kubernetes", "k8s"),
    "Git": ("git",),
    "CI/CD": ("ci/cd", "ci cd", "cicd", "gitlab ci", "github actions"),
    "Machine Learning": ("machine learning", "hoc may", "ml"),
    "Deep Learning": ("deep learning", "hoc sau"),
    "Regression": ("regression", "hoi quy"),
    "Classification": ("classification", "phan loai"),
    "Feature Engineering": ("feature engineering",),
    "Scikit-learn": ("scikit-learn", "scikit learn", "sklearn"),
    "Pandas": ("pandas",),
    "NumPy": ("numpy",),
    "Data Analysis": ("data analysis", "phan tich du lieu"),
    "Data Engineering": ("data engineering",),
    "ETL": ("etl", "elt", "etl/elt"),
    "Apache Spark": ("apache spark", "spark"),
    "Apache Airflow": ("apache airflow", "airflow"),
    "Kafka": ("kafka", "apache kafka"),
    "Flutter": ("flutter",),
    "Dart": ("dart",),
    "SwiftUI": ("swiftui", "swift ui"),
    "Swift": ("swift",),
    "Java": ("java",),
    "Kotlin": ("kotlin",),
    "C++": ("c++", "cpp"),
    "C#": ("c#", "csharp", "c sharp"),
    "PHP": ("php",),
    "Laravel": ("laravel",),
    "Spring Boot": ("spring boot", "springboot", "spring"),
    "Figma": ("figma",),
    "UI/UX": ("ui/ux", "ui ux", "ux", "ui"),
    "Excel": ("excel", "microsoft excel"),
    "Google Sheets": ("google sheets",),
    "Clean Architecture": ("clean architecture",),
}

# Canonical topic label -> alias surface forms.
TOPIC_ALIASES: dict[str, tuple[str, ...]] = {
    "Frontend": ("frontend", "front end", "front-end"),
    "Backend": ("backend", "back end", "back-end"),
    "Web Development": ("web development", "phat trien web", "lap trinh web", "web"),
    "Mobile Development": (
        "mobile development",
        "phat trien di dong",
        "ung dung di dong",
        "mobile",
    ),
    "Data Science": ("data science", "khoa hoc du lieu"),
    "Data Engineering": ("data engineering", "ky thuat du lieu"),
    "Machine Learning": ("machine learning", "hoc may"),
    "Database": ("database", "co so du lieu", "csdl"),
    "DevOps": ("devops", "dev ops"),
    "Cloud": ("cloud", "dien toan dam may"),
    "UI/UX Design": ("ui/ux design", "thiet ke ui ux", "thiet ke giao dien"),
    "Cybersecurity": ("cybersecurity", "an toan thong tin", "bao mat"),
    "Project Management": ("project management", "quan ly du an", "agile", "scrum"),
}


def _build_match_index(
    aliases: dict[str, tuple[str, ...]]
) -> list[tuple[str, str]]:
    """Return (normalized_alias, canonical) sorted longest-first.

    Longest-first avoids matching "api" inside "rest api" before the more
    specific label gets a chance.
    """
    index: list[tuple[str, str]] = []
    for canonical, alias_forms in aliases.items():
        for alias in alias_forms:
            index.append((normalize_text(alias), canonical))
    index.sort(key=lambda pair: len(pair[0]), reverse=True)
    return index


_SKILL_INDEX = _build_match_index(SKILL_ALIASES)
_TOPIC_INDEX = _build_match_index(TOPIC_ALIASES)


# Boundary excludes every character normalize_text keeps inside a token
# ([a-z0-9] plus '+', '#', '.') so 'js' does not match inside 'node.js' and
# 'c' does not match inside 'c++'.
_BOUNDARY_BEFORE = r"(?<![a-z0-9+#.])"
_BOUNDARY_AFTER = r"(?![a-z0-9+#.])"


def _token_boundary_contains(haystack: str, needle: str) -> bool:
    """Whole-token containment so 'r' never matches inside 'react'."""
    if not needle:
        return False
    pattern = _BOUNDARY_BEFORE + re.escape(needle) + _BOUNDARY_AFTER
    return re.search(pattern, haystack) is not None


def canonical_skill(value: str) -> str | None:
    """Map one free-form value to a canonical skill label, if recognized."""
    normalized = normalize_text(value)
    if not normalized:
        return None
    for alias, canonical in _SKILL_INDEX:
        if normalized == alias:
            return canonical
    for alias, canonical in _SKILL_INDEX:
        if _token_boundary_contains(normalized, alias):
            return canonical
    return None


def canonical_topic(value: str) -> str | None:
    """Map one free-form value to a canonical topic label, if recognized."""
    normalized = normalize_text(value)
    if not normalized:
        return None
    for alias, canonical in _TOPIC_INDEX:
        if normalized == alias:
            return canonical
    for alias, canonical in _TOPIC_INDEX:
        if _token_boundary_contains(normalized, alias):
            return canonical
    return None


def _scan(text: str, index: list[tuple[str, str]]) -> list[str]:
    """Return canonical labels whose alias appears in free-form text, in
    first-occurrence order."""
    normalized = normalize_text(text)
    if not normalized:
        return []
    found: dict[str, int] = {}
    for alias, canonical in index:
        if canonical in found:
            continue
        match = re.search(
            _BOUNDARY_BEFORE + re.escape(alias) + _BOUNDARY_AFTER,
            normalized,
        )
        if match:
            found[canonical] = match.start()
    return sorted(found, key=found.get)


def extract_skills(text: str) -> list[str]:
    """Pull all recognized skill labels out of free-form text."""
    return _scan(text, _SKILL_INDEX)


def extract_topics(text: str) -> list[str]:
    """Pull all recognized topic labels out of free-form text."""
    return _scan(text, _TOPIC_INDEX)


def canonicalize_skills(values: Iterable[str]) -> list[str]:
    """Map an existing list of skill-ish strings to canonical labels.

    Unknown values are kept as-is (trimmed) so curated lists are not silently
    dropped; duplicates are removed preserving order.
    """
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        canonical = canonical_skill(value) or str(value).strip()
        if not canonical:
            continue
        key = canonical.casefold()
        if key in seen:
            continue
        seen.add(key)
        result.append(canonical)
    return result


def canonicalize_topics(values: Iterable[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        canonical = canonical_topic(value) or str(value).strip()
        if not canonical:
            continue
        key = canonical.casefold()
        if key in seen:
            continue
        seen.add(key)
        result.append(canonical)
    return result


_LEVEL_MARKERS: dict[str, tuple[str, ...]] = {
    "beginner": ("beginner", "co ban", "can ban", "nhap mon", "introductory", "vo long"),
    "intermediate": ("intermediate", "trung cap", "trung binh"),
    "advanced": ("advanced", "nang cao", "chuyen sau", "expert"),
}


def normalize_level(value: object) -> str | None:
    """Map free-form level text to one of VALID_LEVELS, else None."""
    normalized = normalize_text(value)
    if not normalized:
        return None
    if normalized in VALID_LEVELS:
        return normalized
    for level, markers in _LEVEL_MARKERS.items():
        if any(marker in normalized for marker in markers):
            return level
    return None


_FORMAT_MARKERS: dict[str, tuple[str, ...]] = {
    "online": ("online", "truc tuyen", "tu xa", "e learning", "elearning", "zoom", "google meet"),
    "offline": ("offline", "truc tiep", "tai trung tam", "tai lop", "tai cho"),
    "hybrid": ("hybrid", "ket hop", "linh hoat", "blended"),
}


def normalize_learning_format(value: object) -> str | None:
    """Map free-form format text to one of VALID_LEARNING_FORMATS, else None.

    If both online and offline signals appear, treat it as hybrid.
    """
    normalized = normalize_text(value)
    if not normalized:
        return None
    if normalized in VALID_LEARNING_FORMATS:
        return normalized
    has_online = any(marker in normalized for marker in _FORMAT_MARKERS["online"])
    has_offline = any(marker in normalized for marker in _FORMAT_MARKERS["offline"])
    has_hybrid = any(marker in normalized for marker in _FORMAT_MARKERS["hybrid"])
    if has_hybrid or (has_online and has_offline):
        return "hybrid"
    if has_online:
        return "online"
    if has_offline:
        return "offline"
    return None


# Canonical career role -> alias surface forms. Goal matching compares these
# canonical roles, not raw token overlap, so "Frontend Developer" and "Backend
# Developer" never count as a match just because both contain "developer".
ROLE_ALIASES: dict[str, tuple[str, ...]] = {
    "Frontend Developer": (
        "frontend developer",
        "front end developer",
        "frontend dev",
        "lap trinh frontend",
        "lap trinh front end",
    ),
    "Backend Developer": (
        "backend developer",
        "back end developer",
        "backend dev",
        "lap trinh backend",
        "lap trinh back end",
    ),
    "Fullstack Developer": (
        "fullstack developer",
        "full stack developer",
        "fullstack dev",
        "lap trinh fullstack",
    ),
    "Mobile Developer": (
        "mobile developer",
        "mobile dev",
        "app developer",
        "lap trinh mobile",
        "lap trinh di dong",
        "lap trinh ung dung di dong",
    ),
    "Web Developer": (
        "web developer",
        "web dev",
        "lap trinh web",
    ),
    "Data Engineer": (
        "data engineer",
        "ky su du lieu",
        "ki su du lieu",
    ),
    "Data Analyst": (
        "data analyst",
        "chuyen vien phan tich du lieu",
        "phan tich du lieu",
        "phan tich vien du lieu",
    ),
    "Data Scientist": (
        "data scientist",
        "nha khoa hoc du lieu",
        "khoa hoc du lieu",
    ),
    "Machine Learning Engineer": (
        "machine learning engineer",
        "ml engineer",
        "ai engineer",
        "ky su machine learning",
        "ky su ai",
    ),
    "DevOps Engineer": (
        "devops engineer",
        "devops",
        "ky su devops",
    ),
    "QA Engineer": (
        "qa engineer",
        "tester",
        "kiem thu",
        "kiem thu vien",
        "quality assurance",
    ),
    "UI/UX Designer": (
        "ui/ux designer",
        "ux designer",
        "ui designer",
        "thiet ke ui ux",
        "thiet ke giao dien",
    ),
}

_ROLE_INDEX = _build_match_index(ROLE_ALIASES)


def canonical_role(value: object) -> str | None:
    """Map a free-form career goal to a canonical role label, else None.

    Used for the goal-match dimension: two goals match only when they resolve
    to the same canonical role. Unrecognized goals return None and are compared
    by exact normalized string elsewhere.
    """
    normalized = normalize_text(value)
    if not normalized:
        return None
    for alias, canonical in _ROLE_INDEX:
        if normalized == alias:
            return canonical
    for alias, canonical in _ROLE_INDEX:
        if _token_boundary_contains(normalized, alias):
            return canonical
    return None
