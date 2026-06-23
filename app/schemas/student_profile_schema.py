from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


ProfileLevel = Literal["beginner", "intermediate", "advanced"]
LearningFormat = Literal["online", "offline", "hybrid"]


class StudentProfileCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    intent_text: str = Field(default="", max_length=2000)
    question_answers: dict[str, Any] = Field(default_factory=dict)
    career_goal: str = Field(default="", max_length=300)
    current_level: Optional[ProfileLevel] = None
    current_skills: list[str] = Field(default_factory=list)
    desired_skills: list[str] = Field(default_factory=list)
    interested_topics: list[str] = Field(default_factory=list)
    hours_per_week: Optional[int] = Field(default=None, ge=0)
    learning_format: Optional[LearningFormat] = None


class StudentProfileUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    intent_text: Optional[str] = Field(default=None, max_length=2000)
    question_answers: Optional[dict[str, Any]] = None
    career_goal: Optional[str] = Field(default=None, max_length=300)
    current_level: Optional[ProfileLevel] = None
    current_skills: Optional[list[str]] = None
    desired_skills: Optional[list[str]] = None
    interested_topics: Optional[list[str]] = None
    hours_per_week: Optional[int] = Field(default=None, ge=0)
    learning_format: Optional[LearningFormat] = None


class StudentProfileResponse(BaseModel):
    id: str
    student_id: str
    source_type: str
    intent_text: Optional[str] = None
    question_answers: dict[str, Any] = Field(default_factory=dict)
    career_goal: Optional[str] = None
    current_level: Optional[str] = None
    current_skills: list[str]
    desired_skills: list[str]
    interested_topics: list[str]
    hours_per_week: Optional[int]
    learning_format: Optional[str] = None
    uploaded_file_name: Optional[str] = None
    file_path: Optional[str] = None
    raw_text: Optional[str] = None
    cleaned_text: Optional[str] = None
    created_at: datetime
    updated_at: datetime
