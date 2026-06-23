from __future__ import annotations

import json
import logging
import os
import re
import urllib.error
import urllib.request
from typing import Any

from app.core.config import BASE_DIR

try:
    from dotenv import load_dotenv

    load_dotenv(BASE_DIR / ".env")
except Exception:
    pass

LOGGER = logging.getLogger(__name__)

_CHAT_COMPLETIONS_URL = "https://api.openai.com/v1/chat/completions"
_WARNED_FAILURE = False


def maybe_enrich_course_info(
    cleaned_text: str,
    info: dict[str, Any],
) -> dict[str, Any]:
    if not _enabled() or not _should_enrich_course(info):
        return info
    extracted = _extract_json(
        _course_system_prompt(),
        _compact_input(cleaned_text),
        max_tokens=_env_int("OPENAI_EXTRACTION_MAX_OUTPUT_TOKENS", 800),
    )
    if not extracted:
        return info
    return _merge_course_info(info, extracted)


def maybe_enrich_profile_info(
    cleaned_text: str,
    info: dict[str, Any],
) -> dict[str, Any]:
    if not _enabled() or not _should_enrich_profile(info):
        return info
    extracted = _extract_json(
        _profile_system_prompt(),
        _compact_input(cleaned_text),
        max_tokens=_env_int("OPENAI_EXTRACTION_MAX_OUTPUT_TOKENS", 800),
    )
    if not extracted:
        return info
    return _merge_profile_info(info, extracted)


def _enabled() -> bool:
    return _env_bool("USE_OPENAI_EXTRACTION") and bool(os.getenv("OPENAI_API_KEY", "").strip())


def _should_enrich_course(info: dict[str, Any]) -> bool:
    missing_count = 0
    if not info.get("extracted_title"):
        missing_count += 1
    if not info.get("course_code"):
        missing_count += 1
    if not info.get("extracted_description"):
        missing_count += 1
    if not info.get("extracted_duration_hours"):
        missing_count += 1
    if len(_list(info.get("extracted_skills"))) < 2:
        missing_count += 1
    if not _list(info.get("extracted_topics")):
        missing_count += 1
    if not _list(info.get("extracted_objectives")):
        missing_count += 1
    threshold = _env_int("OPENAI_EXTRACTION_MIN_MISSING_FIELDS", 2)
    return missing_count >= threshold


def _should_enrich_profile(info: dict[str, Any]) -> bool:
    missing_count = 0
    if not info.get("intent_text"):
        missing_count += 1
    if not info.get("career_goal"):
        missing_count += 1
    if not _list(info.get("desired_skills")):
        missing_count += 1
    if not _list(info.get("interested_topics")):
        missing_count += 1
    threshold = _env_int("OPENAI_EXTRACTION_MIN_MISSING_FIELDS", 2)
    return missing_count >= threshold


def _extract_json(system_prompt: str, user_text: str, *, max_tokens: int) -> dict[str, Any] | None:
    global _WARNED_FAILURE

    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    model = os.getenv("OPENAI_EXTRACTION_MODEL", "gpt-5.4-mini").strip()
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_text},
        ],
        "response_format": {"type": "json_object"},
        "max_completion_tokens": max_tokens,
    }

    request = urllib.request.Request(
        _CHAT_COMPLETIONS_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(
            request,
            timeout=_env_float("OPENAI_EXTRACTION_TIMEOUT_SECONDS", 12.0),
        ) as response:
            body = json.loads(response.read().decode("utf-8"))
        content = body["choices"][0]["message"]["content"]
        parsed = json.loads(content)
        return parsed if isinstance(parsed, dict) else None
    except (OSError, urllib.error.HTTPError, urllib.error.URLError, KeyError, IndexError, ValueError) as exc:
        if not _WARNED_FAILURE:
            LOGGER.warning("OpenAI extraction failed; using local extractor only: %s", exc)
            _WARNED_FAILURE = True
        return None


def _course_system_prompt() -> str:
    return (
        "Extract course metadata from Vietnamese/English course text. "
        "Return compact JSON only with keys: extracted_title, course_code, "
        "extracted_description, extracted_level, extracted_skills, extracted_topics, "
        "extracted_objectives, extracted_prerequisites, extracted_tools, "
        "extracted_duration_hours, summary. Use null/[] when unknown. "
        "extracted_level must be beginner/intermediate/advanced/null. "
        "extracted_duration_hours must be an integer hour count or null. "
        "Do not invent content absent from the text."
    )


def _profile_system_prompt() -> str:
    return (
        "Extract a learner intent profile from Vietnamese/English text. "
        "Return compact JSON only with keys: intent_text, career_goal, current_level, "
        "current_skills, desired_skills, interested_topics, hours_per_week, learning_format. "
        "current_level must be beginner/intermediate/advanced/null. "
        "learning_format must be online/offline/hybrid/null. "
        "hours_per_week must be an integer or null. Do not invent facts absent from the text."
    )


def _merge_course_info(local: dict[str, Any], extracted: dict[str, Any]) -> dict[str, Any]:
    result = dict(local)
    scalar_keys = (
        "extracted_title",
        "course_code",
        "extracted_description",
        "extracted_level",
        "extracted_duration_hours",
        "summary",
    )
    for key in scalar_keys:
        value = extracted.get(key)
        if value not in (None, "", []):
            result[key] = value
    for key in (
        "extracted_skills",
        "extracted_topics",
        "extracted_objectives",
        "extracted_prerequisites",
        "extracted_tools",
    ):
        result[key] = _merge_list(_list(local.get(key)), _list(extracted.get(key)))
    return result


def _merge_profile_info(local: dict[str, Any], extracted: dict[str, Any]) -> dict[str, Any]:
    result = dict(local)
    for key in (
        "intent_text",
        "career_goal",
        "current_level",
        "hours_per_week",
        "learning_format",
    ):
        value = extracted.get(key)
        if value not in (None, "", []):
            result[key] = value
    for key in ("current_skills", "desired_skills", "interested_topics"):
        result[key] = _merge_list(_list(local.get(key)), _list(extracted.get(key)))
    return result


def _compact_input(text: str) -> str:
    compact = re.sub(r"\s+", " ", str(text or "")).strip()
    max_chars = _env_int("OPENAI_EXTRACTION_MAX_INPUT_CHARS", 3500)
    return compact[:max(800, max_chars)]


def _merge_list(left: list[str], right: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in [*left, *right]:
        text = str(value).strip()
        key = text.casefold()
        if text and key not in seen:
            seen.add(key)
            result.append(text)
    return result


def _list(value: Any) -> list[str]:
    if isinstance(value, (list, tuple, set)):
        return [str(item).strip() for item in value if str(item).strip()]
    if value is None:
        return []
    text = str(value).strip()
    return [text] if text else []


def _env_bool(name: str) -> bool:
    value = os.getenv(name, "")
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name, "").strip()
    if not value:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    value = os.getenv(name, "").strip()
    if not value:
        return default
    try:
        return float(value)
    except ValueError:
        return default
