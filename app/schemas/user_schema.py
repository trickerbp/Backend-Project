
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


UserRole = Literal["student", "admin"]


class UserCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=128)
    role: Literal["student"] = "student"


class UserPublic(BaseModel):
    id: str
    name: str
    email: EmailStr
    role: UserRole
    created_at: datetime
