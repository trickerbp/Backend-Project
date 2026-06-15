from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ScoreDetail(BaseModel):
    skill_gap_score: float = 0
    topic_match_score: float = 0
    level_match_score: float = 0
    goal_match_score: float = 0
    duration_match_score: float = 0
    text_similarity_score: float = 0


class RecommendationResultItem(BaseModel):
    course_id: str
    title: Optional[str] = None
    course_code: Optional[str] = None
    level: Optional[str] = None
    score: float
    matched_reasons: list[str] = []
    matched_skills: list[str] = []
    missing_skills: list[str] = []
    matched_topics: list[str] = []
    matched_resource_ids: list[str] = []
    prerequisites_met: bool = True
    unmet_prerequisites: list[str] = []
    score_detail: ScoreDetail


class RecommendationResponse(BaseModel):
    id: str
    student_id: str
    student_profile_id: str
    results: list[RecommendationResultItem]
    created_at: datetime


class GenerateRecommendationRequest(BaseModel):
    student_profile_id: Optional[str] = None
