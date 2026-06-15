from __future__ import annotations

from typing import Any

from fastapi import Depends, HTTPException, status

from app.dependencies.auth_dependency import get_current_user


def require_roles(allowed_roles: list[str]):
    async def dependency(
        current_user: dict[str, Any] = Depends(get_current_user),
    ) -> dict[str, Any]:
        if current_user.get('role') not in set(allowed_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail='Permission denied',
            )
        return current_user

    return dependency
