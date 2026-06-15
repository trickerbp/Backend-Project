from __future__ import annotations

from fastapi import APIRouter, Depends

from app.database.mongodb import get_database
from app.dependencies.auth_dependency import require_admin
from app.models.user_model import user_to_public
from app.schemas.user_schema import UserPublic


router = APIRouter(prefix='/api/users', tags=['Users'])


@router.get('', response_model=list[UserPublic])
async def list_users(
    role: str | None = None,
    current_user: dict = Depends(require_admin),
) -> list[UserPublic]:
    db = get_database()
    query = {'role': role} if role else {}
    users = await db.users.find(query).sort('created_at', -1).to_list(length=None)
    return [user_to_public(user) for user in users]


@router.get('/teachers', response_model=list[UserPublic])
async def list_teachers(
    current_user: dict = Depends(require_admin),
) -> list[UserPublic]:
    db = get_database()
    users = await db.users.find({'role': 'teacher'}).sort('name', 1).to_list(length=None)
    return [user_to_public(user) for user in users]


@router.get('/students', response_model=list[UserPublic])
async def list_students(
    current_user: dict = Depends(require_admin),
) -> list[UserPublic]:
    db = get_database()
    users = await db.users.find({'role': 'student'}).sort('name', 1).to_list(length=None)
    return [user_to_public(user) for user in users]
