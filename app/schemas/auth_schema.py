
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.schemas.user_schema import UserPublic


class LoginRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    email: EmailStr
    password: str = Field(..., min_length=6, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserPublic
