from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


CourseLevel = Literal["beginner", "intermediate", "advanced"]
CourseStatus = Literal["draft", "active", "archived"]


class CourseCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    title: str = Field(..., min_length=2, max_length=200)
    course_code: str = Field(..., min_length=1, max_length=50)
    description: str = Field(default="", max_length=5000)
    level: CourseLevel = "beginner"
    target_goals: list[str] = Field(default_factory=list)
    manual_tags: list[str] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)
    duration_hours: Optional[int] = Field(default=None, ge=0)
    teacher_id: Optional[str] = Field(default=None, min_length=1)
    status: CourseStatus = "draft"


class CourseUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    title: Optional[str] = Field(default=None, min_length=2, max_length=200)
    course_code: Optional[str] = Field(default=None, min_length=1, max_length=50)
    description: Optional[str] = Field(default=None, max_length=5000)
    level: Optional[CourseLevel] = None
    target_goals: Optional[list[str]] = None
    manual_tags: Optional[list[str]] = None
    tools: Optional[list[str]] = None
    duration_hours: Optional[int] = Field(default=None, ge=0)
    teacher_id: Optional[str] = Field(default=None, min_length=1)
    status: Optional[CourseStatus] = None


class CourseResponse(BaseModel):
    id: str
    title: str
    course_code: str
    description: str
    level: str
    target_goals: list[str]
    manual_tags: list[str]
    extracted_skills: list[str]
    extracted_topics: list[str]
    extracted_objectives: list[str]
    extracted_prerequisites: list[str]
    tools: list[str]
    duration_hours: Optional[int]
    teacher_id: Optional[str]
    status: str
    created_at: datetime
    updated_at: datetime
