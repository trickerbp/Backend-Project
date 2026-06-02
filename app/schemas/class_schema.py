from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


ClassStatus = Literal["open", "closed"]


class ClassBase(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    class_name: str = Field(..., min_length=2, max_length=150)
    description: str = Field(..., min_length=5, max_length=2000)
    teacher_name: str = Field(..., min_length=2, max_length=120)
    schedule: str = Field(..., min_length=2, max_length=200)
    room: str = Field(..., min_length=1, max_length=50)
    max_students: int = Field(..., ge=1, le=500)
    current_students: int = Field(default=0, ge=0, le=500)
    status: ClassStatus = "open"

    @model_validator(mode="after")
    def validate_capacity(self) -> "ClassBase":
        if self.current_students > self.max_students:
            raise ValueError("current_students cannot be greater than max_students")
        return self


class ClassCreate(ClassBase):
    current_students: int = Field(default=0, ge=0, le=500)


class ClassUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    class_name: str | None = Field(default=None, min_length=2, max_length=150)
    description: str | None = Field(default=None, min_length=5, max_length=2000)
    teacher_name: str | None = Field(default=None, min_length=2, max_length=120)
    schedule: str | None = Field(default=None, min_length=2, max_length=200)
    room: str | None = Field(default=None, min_length=1, max_length=50)
    max_students: int | None = Field(default=None, ge=1, le=500)
    current_students: int | None = Field(default=None, ge=0, le=500)
    status: ClassStatus | None = None


class ClassResponse(ClassBase):
    id: str
    created_by: str
    created_at: datetime
    updated_at: datetime | None = None
