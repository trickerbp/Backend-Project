
from __future__ import annotations

from typing import Any

from bson import ObjectId
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.core.security import decode_access_token
from app.database.mongodb import get_database


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def _credentials_exception() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict[str, Any]:
    payload = decode_access_token(token)
    if payload is None:
        raise _credentials_exception()

    user_id = payload.get("sub")
    if not user_id or not ObjectId.is_valid(user_id):
        raise _credentials_exception()

    db = get_database()
    user = await db.users.find_one({"_id": ObjectId(user_id)})
    if user is None:
        raise _credentials_exception()

    return user


async def require_admin(
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin permission required",
        )
    return current_user


async def require_student(
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    if current_user.get("role") != "student":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Student permission required",
        )
    return current_user
