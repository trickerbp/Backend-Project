from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


EnrollmentStatus = Literal["pending", "approved", "rejected"]


class EnrollmentCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    class_id: str = Field(..., min_length=1)
    note: str | None = Field(default=None, max_length=500)


class EnrollmentResponse(BaseModel):
    id: str
    student_id: str
    class_id: str
    status: EnrollmentStatus
    note: str | None = None
    created_at: datetime
    updated_at: datetime | None = None
    approved_by: str | None = None
