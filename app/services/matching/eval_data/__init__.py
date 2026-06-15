"""Hand-built evaluation data (gold set) for the recommender."""
from __future__ import annotations

from app.services.matching.eval_data.gold_set import (
    COURSES,
    RELEVANCE_RUBRIC,
    STUDENTS,
    binary_relevant,
)


__all__ = ["COURSES", "STUDENTS", "RELEVANCE_RUBRIC", "binary_relevant"]
