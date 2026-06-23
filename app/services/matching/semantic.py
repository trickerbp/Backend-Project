from __future__ import annotations

import json
import logging
import math
import os
import urllib.error
import urllib.request
from typing import Any, Callable, Iterable, Mapping

from app.core.config import BASE_DIR
from app.services.matching.skill_taxonomy import (
    canonical_role,
    extract_skills,
    extract_topics,
    skill_similarity,
    topic_similarity,
)
from app.services.matching.text_similarity import text_similarity

try:
    from dotenv import load_dotenv

    load_dotenv(BASE_DIR / ".env")
except Exception:
    pass

LOGGER = logging.getLogger(__name__)

_OPENAI_EMBEDDINGS_URL = "https://api.openai.com/v1/embeddings"
_EMBEDDING_CACHE: dict[tuple[str, str, int], list[float]] = {}
_WARNED_OPENAI_FAILURE = False


def semantic_similarity(
    profile: Mapping[str, Any],
    course: Mapping[str, Any],
) -> float | None:
    """Semantic match score in [0, 1], with OpenAI embeddings as opt-in boost.

    The local score is deterministic and taxonomy-aware. When embedding
    matching is enabled, the embedding score is used only if it is stronger.
    """
    local = _local_semantic_similarity(profile, course)

    if not _embedding_enabled():
        return local
    if not _should_call_embedding(local):
        return local

    profile_text = _profile_text(profile)
    course_text = _course_text(course)
    if not profile_text or not course_text:
        return local

    embedding_score = _openai_embedding_similarity(profile_text, course_text)
    if embedding_score is None:
        return local
    if local is None:
        return embedding_score
    return max(local, embedding_score)


def _local_semantic_similarity(
    profile: Mapping[str, Any],
    course: Mapping[str, Any],
) -> float | None:
    skill_targets = _list(profile.get("desired_skills"))
    if not skill_targets:
        skill_targets = extract_skills(profile.get("content_text") or "")
    course_skills = _list(course.get("course_skills"))
    course_skills.extend(_list(course.get("extracted_skills")))
    course_skills.extend(_list(course.get("manual_tags")))
    course_skills.extend(extract_skills(course.get("content_text") or ""))

    topic_targets = _list(profile.get("interested_topics"))
    if not topic_targets:
        topic_targets = extract_topics(profile.get("content_text") or "")
    course_topics = _list(course.get("course_topics"))
    course_topics.extend(_list(course.get("extracted_topics")))
    course_topics.extend(extract_topics(course.get("content_text") or ""))

    skill_score = _average_best_similarity(
        skill_targets,
        course_skills,
        skill_similarity,
    )
    topic_score = _average_best_similarity(
        topic_targets,
        course_topics,
        topic_similarity,
    )
    goal_score = _semantic_goal_score(profile, course)
    text_score = text_similarity(_profile_text(profile), _course_text(course))

    weighted_parts = [
        (skill_score, 0.45),
        (topic_score, 0.25),
        (goal_score, 0.15),
        (text_score if text_score > 0 else None, 0.15),
    ]
    active = [(score, weight) for score, weight in weighted_parts if score is not None]
    if not active:
        return None
    total_weight = sum(weight for _, weight in active)
    score = sum(score * weight for score, weight in active) / total_weight
    return max(0.0, min(1.0, score))


def _semantic_goal_score(
    profile: Mapping[str, Any],
    course: Mapping[str, Any],
) -> float | None:
    goal = str(profile.get("career_goal") or "").strip()
    if not goal:
        return None
    targets = _list(course.get("target_goals"))
    if not targets:
        return None

    goal_role = canonical_role(goal)
    best = 0.0
    compared_known_roles = False
    for target in targets:
        target_role = canonical_role(target)
        if goal_role and target_role:
            compared_known_roles = True
            if goal_role == target_role:
                return 1.0
            continue
        best = max(best, text_similarity(goal, target))
    if compared_known_roles:
        return 0.0
    return best if best > 0 else 0.0


def _average_best_similarity(
    targets: Iterable[str],
    candidates: Iterable[str],
    scorer: Callable[[object, object], float],
) -> float | None:
    target_values = _unique(targets)
    candidate_values = _unique(candidates)
    if not target_values:
        return None
    if not candidate_values:
        return 0.0

    total = 0.0
    for target in target_values:
        total += max(scorer(target, candidate) for candidate in candidate_values)
    return total / len(target_values)


def _openai_embedding_similarity(left_text: str, right_text: str) -> float | None:
    vectors = _openai_embeddings([left_text, right_text])
    if vectors is None or len(vectors) != 2:
        return None
    left, right = vectors
    if left is None or right is None:
        return None
    return _normalize_embedding_cosine(_cosine(left, right))


def _openai_embeddings(texts: list[str]) -> list[list[float] | None] | None:
    global _WARNED_OPENAI_FAILURE

    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        return None

    model = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small").strip()
    dimensions = _env_int("OPENAI_EMBEDDING_DIMENSIONS", 0)
    clipped_texts = [_clip_text(text) for text in texts]
    cache_keys = [(model, text, dimensions) for text in clipped_texts]
    results: list[list[float] | None] = [_EMBEDDING_CACHE.get(key) for key in cache_keys]
    missing_indexes = [
        index for index, vector in enumerate(results) if vector is None and clipped_texts[index]
    ]
    if not missing_indexes:
        return results

    payload: dict[str, Any] = {
        "model": model,
        "input": [clipped_texts[index] for index in missing_indexes],
    }
    if dimensions > 0:
        payload["dimensions"] = dimensions

    request = urllib.request.Request(
        _OPENAI_EMBEDDINGS_URL,
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
            timeout=_env_float("OPENAI_EMBEDDING_TIMEOUT_SECONDS", 8.0),
        ) as response:
            body = json.loads(response.read().decode("utf-8"))
    except (OSError, urllib.error.HTTPError, urllib.error.URLError, ValueError) as exc:
        if not _WARNED_OPENAI_FAILURE:
            LOGGER.warning("OpenAI embedding matching failed; using local semantic score: %s", exc)
            _WARNED_OPENAI_FAILURE = True
        return None

    try:
        data = sorted(body["data"], key=lambda item: item.get("index", 0))
        vectors = [
            [float(value) for value in item["embedding"]]
            for item in data
        ]
    except (KeyError, IndexError, TypeError, ValueError):
        if not _WARNED_OPENAI_FAILURE:
            LOGGER.warning("OpenAI embedding response had an unexpected shape")
            _WARNED_OPENAI_FAILURE = True
        return None

    for result_index, vector in zip(missing_indexes, vectors):
        _EMBEDDING_CACHE[cache_keys[result_index]] = vector
        results[result_index] = vector
    return results


def _normalize_embedding_cosine(value: float) -> float:
    # Raw embedding cosine often has a non-zero baseline for unrelated text.
    # Convert roughly [0.55, 0.85] into [0, 1] so weak context cannot rank alone.
    return max(0.0, min(1.0, (value - 0.55) / 0.30))


def _cosine(left: list[float], right: list[float]) -> float:
    if len(left) != len(right):
        return 0.0
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if not left_norm or not right_norm:
        return 0.0
    return sum(a * b for a, b in zip(left, right)) / (left_norm * right_norm)


def _embedding_enabled() -> bool:
    return _env_bool("USE_EMBEDDING_MATCHING") or _env_bool(
        "USE_OPENAI_SEMANTIC_MATCHING"
    )


def _should_call_embedding(local_score: float | None) -> bool:
    """Use paid embeddings only for ambiguous cases."""
    if local_score is None:
        return True
    high = _env_float("OPENAI_EMBEDDING_SKIP_IF_LOCAL_AT_LEAST", 0.72)
    low = _env_float("OPENAI_EMBEDDING_SKIP_IF_LOCAL_BELOW", 0.12)
    if local_score >= high:
        return False
    if local_score <= low:
        return _env_bool("OPENAI_EMBEDDING_EXPAND_LOW_CONFIDENCE")
    return True


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


def _profile_text(profile: Mapping[str, Any]) -> str:
    intent_text = str(profile.get("intent_text") or "").strip()
    question_answers = _answers_text(profile.get("question_answers"))
    content_text = "" if intent_text else _excerpt(profile.get("content_text"), 500)
    return " ".join(
        _compact_parts(
            [
                intent_text,
                question_answers,
                profile.get("career_goal"),
                profile.get("desired_skills"),
                profile.get("interested_topics"),
                content_text,
            ]
        )
    )


def _course_text(course: Mapping[str, Any]) -> str:
    fallback_content = ""
    if not course.get("description"):
        fallback_content = _excerpt(course.get("content_text"), 500)
    return " ".join(
        _compact_parts(
            [
                course.get("title"),
                course.get("course_code"),
                course.get("description"),
                course.get("target_goals"),
                course.get("manual_tags"),
                course.get("extracted_skills"),
                course.get("extracted_topics"),
                fallback_content,
            ]
        )
    )


def _compact_parts(values: Iterable[Any]) -> list[str]:
    parts: list[str] = []
    seen: set[str] = set()
    for value in values:
        if isinstance(value, (list, tuple, set)):
            for item in value:
                text = str(item).strip()
                key = text.casefold()
                if text and key not in seen:
                    seen.add(key)
                    parts.append(text)
            continue
        text = str(value or "").strip()
        key = text.casefold()
        if text and key not in seen:
            seen.add(key)
            parts.append(text)
    return parts


def _clip_text(text: str) -> str:
    max_chars = _env_int("OPENAI_EMBEDDING_MAX_INPUT_CHARS", 900)
    return " ".join(str(text or "").split())[:max(200, max_chars)]


def _excerpt(value: Any, max_length: int) -> str:
    return " ".join(str(value or "").split())[:max_length]


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


def _list(value: Any) -> list[str]:
    if isinstance(value, (list, tuple, set)):
        return [str(item).strip() for item in value if str(item).strip()]
    if value is None:
        return []
    text = str(value).strip()
    return [text] if text else []


def _unique(values: Iterable[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = str(value).strip()
        key = text.casefold()
        if text and key not in seen:
            seen.add(key)
            result.append(text)
    return result
