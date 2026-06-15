from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from app.services.matching.skill_taxonomy import canonical_role
from app.services.matching.text_similarity import text_similarity


__all__ = [
    "ScoreWeights",
    "DimensionScores",
    "CourseMatch",
    "score_course_for_student",
]


@dataclass(frozen=True, slots=True)
class ScoreWeights:
    """Relative weight of each scoring dimension.

    Dimensions split into two roles:
      * relevance (skill_gap, topic, goal): decide whether a course is relevant
        to the learner at all.
      * context (level, duration): modulate ranking among relevant courses but
        never create relevance on their own.

    Only dimensions the learner actually provides input for are counted in the
    denominator (dynamic denominator), so a missing field does not drag the
    score down as an implicit zero. text_similarity is a separate additive
    bonus, never part of the denominator.
    """

    # Tuned on the gold set (scripts/tune_weights.py) by max nDCG@5 under
    # leave-one-student-out CV: LOSO 0.96 ~ in-sample 0.964, so the choice
    # generalizes rather than overfits. The grid pushed the context/bonus
    # dimensions to their floor, i.e. skill_gap should dominate (~4x the rest).
    skill_gap: float = 0.40
    topic: float = 0.10
    goal: float = 0.10
    level: float = 0.08
    duration: float = 0.04
    # Additive bonus multiplier applied to the cosine similarity (0..1).
    text_similarity_bonus: float = 0.05


# Dimensions that establish relevance. If every applicable one scores zero, the
# course is treated as irrelevant regardless of level/duration fit.
_RELEVANCE_DIMENSIONS = ("skill_gap", "topic", "goal")


@dataclass(frozen=True, slots=True)
class DimensionScores:
    skill_gap: float = 0.0
    topic: float = 0.0
    level: float = 0.0
    goal: float = 0.0
    duration: float = 0.0
    text_similarity: float = 0.0


@dataclass(slots=True)
class CourseMatch:
    course_id: str | None
    title: str | None
    course_code: str | None
    level: str | None
    score: float
    score_detail: DimensionScores
    matched_skills: list[str] = field(default_factory=list)
    missing_skills: list[str] = field(default_factory=list)
    matched_topics: list[str] = field(default_factory=list)
    matched_reasons: list[str] = field(default_factory=list)
    prerequisites_met: bool = True
    unmet_prerequisites: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "course_id": self.course_id,
            "title": self.title,
            "course_code": self.course_code,
            "level": self.level,
            "score": round(self.score, 4),
            "matched_skills": self.matched_skills,
            "missing_skills": self.missing_skills,
            "matched_topics": self.matched_topics,
            "matched_reasons": self.matched_reasons,
            "prerequisites_met": self.prerequisites_met,
            "unmet_prerequisites": self.unmet_prerequisites,
            "score_detail": {
                "skill_gap_score": round(self.score_detail.skill_gap, 4),
                "topic_match_score": round(self.score_detail.topic, 4),
                "level_match_score": round(self.score_detail.level, 4),
                "goal_match_score": round(self.score_detail.goal, 4),
                "duration_match_score": round(self.score_detail.duration, 4),
                "text_similarity_score": round(
                    self.score_detail.text_similarity, 4
                ),
            },
        }


_LEVEL_ORDER = {"beginner": 0, "intermediate": 1, "advanced": 2}

# Unmet prerequisites gate the course down rather than excluding it.
_PREREQUISITE_PENALTY = 0.5


def _lower_set(values: list[str] | None) -> set[str]:
    return {str(v).strip().casefold() for v in (values or []) if str(v).strip()}


def _display_map(values: list[str] | None) -> dict[str, str]:
    """casefold key -> first-seen display form, for human-readable reasons."""
    mapping: dict[str, str] = {}
    for value in values or []:
        text = str(value).strip()
        if text:
            mapping.setdefault(text.casefold(), text)
    return mapping


def _course_skill_pool(course: Mapping[str, Any]) -> dict[str, str]:
    pool: dict[str, str] = {}
    for source_key in ("course_skills", "extracted_skills", "manual_tags"):
        pool.update(_display_map(course.get(source_key)))
    return pool


def _score_skill_gap(
    profile: Mapping[str, Any],
    course: Mapping[str, Any],
) -> tuple[float | None, list[str], list[str]]:
    """Reward a course for teaching skills the student wants but lacks.

    Returns (score, matched_display, missing_display). ``score`` is None when
    the student declared no desired skills (dimension not applicable), so it is
    excluded from the denominator rather than counted as zero. Otherwise
    score = covered_gap / total_gap.
    """
    current = _lower_set(profile.get("current_skills"))
    desired_display = _display_map(profile.get("desired_skills"))
    if not desired_display:
        return None, [], []

    course_keys = set(_course_skill_pool(course))

    gap_keys = set(desired_display) - current
    target_keys = gap_keys or set(desired_display)
    covered = target_keys & course_keys
    missing = target_keys - course_keys
    score = len(covered) / len(target_keys)
    matched_display = [desired_display[k] for k in sorted(covered)]
    missing_display = [desired_display[k] for k in sorted(missing)]
    return score, matched_display, missing_display


def _score_topic(
    profile: Mapping[str, Any],
    course: Mapping[str, Any],
) -> tuple[float | None, list[str]]:
    """None when the student declared no interested topics."""
    interested_display = _display_map(profile.get("interested_topics"))
    if not interested_display:
        return None, []
    course_topics = _lower_set(course.get("course_topics")) | _lower_set(
        course.get("extracted_topics")
    )
    hits = set(interested_display) & course_topics
    score = len(hits) / len(interested_display)
    matched_display = [interested_display[k] for k in sorted(hits)]
    return score, matched_display


def _score_goal(profile: Mapping[str, Any], course: Mapping[str, Any]) -> float | None:
    """Goal match by canonical role, not token overlap.

    None when the student stated no career goal. Otherwise 1.0 when the goal and
    one of the course target-goals resolve to the same canonical role (or match
    exactly after normalization), else 0.0. No partial credit for sharing a
    generic word like "developer".
    """
    goal_raw = (profile.get("career_goal") or "").strip()
    if not goal_raw:
        return None
    target_goals = [
        str(t).strip() for t in (course.get("target_goals") or []) if str(t).strip()
    ]
    if not target_goals:
        return 0.0

    goal_role = canonical_role(goal_raw)
    goal_key = goal_raw.casefold()
    for target in target_goals:
        target_role = canonical_role(target)
        if goal_role is not None and target_role is not None:
            if goal_role == target_role:
                return 1.0
        elif target.casefold() == goal_key:
            return 1.0
    return 0.0


def _score_level(
    profile: Mapping[str, Any], course: Mapping[str, Any]
) -> float | None:
    """None when either side has no level."""
    student_level = (profile.get("current_level") or "").strip().casefold()
    course_level = (course.get("level") or "").strip().casefold()
    if student_level not in _LEVEL_ORDER or course_level not in _LEVEL_ORDER:
        return None
    distance = _LEVEL_ORDER[course_level] - _LEVEL_ORDER[student_level]
    if distance == 0:
        return 1.0
    if distance == 1:
        return 0.8  # one step above: ideal "next course"
    if distance == -1:
        return 0.4  # a review course one step below
    return 0.2  # two steps apart: weak fit


def _score_duration(
    profile: Mapping[str, Any],
    course: Mapping[str, Any],
) -> float | None:
    """Fit of course length to the learner's weekly time budget.

    None when duration or weekly hours is unknown. Otherwise based on estimated
    weeks-to-finish = duration_hours / hours_per_week.
    """
    duration_hours = course.get("duration_hours")
    hours_per_week = profile.get("hours_per_week")
    if not duration_hours or not hours_per_week:
        return None
    try:
        weeks = float(duration_hours) / float(hours_per_week)
    except (TypeError, ValueError, ZeroDivisionError):
        return None
    if weeks <= 0:
        return None
    if weeks <= 8:
        return 1.0
    if weeks <= 12:
        return 0.8
    if weeks <= 20:
        return 0.5
    return 0.2


def _score_text_similarity(
    profile: Mapping[str, Any],
    course: Mapping[str, Any],
) -> float:
    return text_similarity(
        str(profile.get("content_text") or ""),
        str(course.get("content_text") or ""),
    )


def _check_prerequisites(
    profile: Mapping[str, Any],
    course: Mapping[str, Any],
) -> tuple[bool, list[str]]:
    """A prerequisite is a gate, not a bonus.

    Resolve only KNOWN skills named in each prerequisite line; free text that
    names no recognized skill is treated as informational (met). A prerequisite
    is unmet when it names a known skill the student does not have.
    """
    from app.services.matching.skill_taxonomy import extract_skills

    current = _lower_set(profile.get("current_skills"))
    unmet: list[str] = []
    for prerequisite in course.get("extracted_prerequisites") or []:
        required = extract_skills(str(prerequisite))
        required_keys = {skill.casefold() for skill in required}
        if required_keys and not (required_keys & current):
            unmet.append(str(prerequisite).strip())
    return (len(unmet) == 0), unmet


def score_course_for_student(
    profile: Mapping[str, Any],
    course: Mapping[str, Any],
    weights: ScoreWeights | None = None,
) -> CourseMatch:
    """Score one normalized course against one normalized student profile.

    Both inputs are the canonical dicts produced by normalize.py. Pure function:
    no I/O, deterministic.

    Scoring model:
      1. Score each dimension; dimensions the learner gave no input for return
         None and are excluded from the weighted average (dynamic denominator).
      2. Relevance gate: if at least one relevance dimension applies and they
         all score zero, the course is irrelevant -> final score 0 (level and
         duration cannot rescue an irrelevant course).
      3. text_similarity adds a small bonus on top (never drags the score down).
      4. Unmet prerequisites halve the final score.
    """
    weights = weights or ScoreWeights()

    skill_score, matched_skills, missing_skills = _score_skill_gap(profile, course)
    topic_score, matched_topics = _score_topic(profile, course)
    goal_score = _score_goal(profile, course)
    level_score = _score_level(profile, course)
    duration_score = _score_duration(profile, course)
    similarity_score = _score_text_similarity(profile, course)
    prerequisites_met, unmet = _check_prerequisites(profile, course)

    dimension_values = {
        "skill_gap": skill_score,
        "topic": topic_score,
        "goal": goal_score,
        "level": level_score,
        "duration": duration_score,
    }
    dimension_weights = {
        "skill_gap": weights.skill_gap,
        "topic": weights.topic,
        "goal": weights.goal,
        "level": weights.level,
        "duration": weights.duration,
    }

    detail = DimensionScores(
        skill_gap=skill_score or 0.0,
        topic=topic_score or 0.0,
        level=level_score or 0.0,
        goal=goal_score or 0.0,
        duration=duration_score or 0.0,
        text_similarity=similarity_score,
    )

    applicable = {
        name: value
        for name, value in dimension_values.items()
        if value is not None
    }
    relevance_applicable = {
        name: applicable[name]
        for name in _RELEVANCE_DIMENSIONS
        if name in applicable
    }

    if not relevance_applicable:
        # The learner gave no relevance signal at all (no desired skills, no
        # topics, no career goal). Level/duration cannot establish relevance on
        # their own, so fall back to content similarity as the only base. This
        # keeps an unrelated course from scoring high just because its level and
        # schedule happen to fit.
        base = similarity_score
    elif not any(value > 0 for value in relevance_applicable.values()):
        # Relevance was assessable and every relevance dimension scored zero:
        # the course is not relevant to this learner. Gate to zero regardless of
        # level/duration fit.
        base = 0.0
    else:
        # Relevant course: weighted average over every applicable dimension
        # (relevance + context), then a small additive text-similarity bonus.
        denominator = sum(dimension_weights[name] for name in applicable)
        weighted = sum(
            dimension_weights[name] * value for name, value in applicable.items()
        )
        base = weighted / denominator if denominator else 0.0
        base = min(1.0, base + weights.text_similarity_bonus * similarity_score)

    final = base
    if not prerequisites_met:
        final *= _PREREQUISITE_PENALTY

    reasons = _build_reasons(
        matched_skills=matched_skills,
        missing_skills=missing_skills,
        matched_topics=matched_topics,
        level_score=level_score,
        course_level=course.get("level"),
        goal_score=goal_score,
        career_goal=profile.get("career_goal"),
        duration_score=duration_score,
        similarity_score=similarity_score,
        prerequisites_met=prerequisites_met,
        unmet=unmet,
    )

    return CourseMatch(
        course_id=course.get("course_id"),
        title=course.get("title"),
        course_code=course.get("course_code"),
        level=course.get("level"),
        score=final,
        score_detail=detail,
        matched_skills=matched_skills,
        missing_skills=missing_skills,
        matched_topics=matched_topics,
        matched_reasons=reasons,
        prerequisites_met=prerequisites_met,
        unmet_prerequisites=unmet,
    )


def _build_reasons(
    *,
    matched_skills: list[str],
    missing_skills: list[str],
    matched_topics: list[str],
    level_score: float | None,
    course_level: str | None,
    goal_score: float | None,
    career_goal: str | None,
    duration_score: float | None,
    similarity_score: float,
    prerequisites_met: bool,
    unmet: list[str],
) -> list[str]:
    """Human-readable Vietnamese explanations for why a course was suggested."""
    reasons: list[str] = []

    if matched_skills:
        reasons.append(
            "Dạy kỹ năng bạn muốn học mà chưa có: " + ", ".join(matched_skills)
        )
    if matched_topics:
        reasons.append(
            "Phù hợp lĩnh vực bạn quan tâm: " + ", ".join(matched_topics)
        )
    if goal_score and goal_score >= 1.0 and career_goal:
        reasons.append(f"Đúng mục tiêu nghề nghiệp: {career_goal}")
    if level_score is not None and level_score >= 0.8 and course_level:
        reasons.append(f"Phù hợp trình độ hiện tại (mức {course_level})")
    if duration_score is not None and duration_score >= 0.8:
        reasons.append("Thời lượng phù hợp với quỹ thời gian học của bạn")
    if similarity_score >= 0.3:
        reasons.append("Nội dung khóa học sát với nhu cầu bạn mô tả")
    if missing_skills:
        reasons.append(
            "Lưu ý: khóa học chưa bao gồm: " + ", ".join(missing_skills)
        )
    if not prerequisites_met and unmet:
        reasons.append(
            "Cảnh báo: bạn có thể chưa đủ điều kiện tiên quyết: "
            + ", ".join(unmet)
        )
    return reasons
