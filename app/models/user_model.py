from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


USERS_COLLECTION = "users"

VALID_ROLES = {"admin", "teacher", "student"}


def create_user_document(
    name: str,
    email: str,
    password_hash: str,
    role: str,
) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    return {
        "name": name,
        "email": email.lower(),
        "password_hash": password_hash,
        "role": role,
        "created_at": now,
        "updated_at": now,
    }


def user_to_public(user: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(user["_id"]),
        "name": user["name"],
        "email": user["email"],
        "role": user["role"],
        "created_at": user["created_at"],
    }
