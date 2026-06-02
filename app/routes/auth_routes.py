
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.security import create_access_token, hash_password, verify_password
from app.database.mongodb import get_database
from app.dependencies.auth_dependency import get_current_user
from app.models.user_model import create_user_document, user_to_public
from app.schemas.auth_schema import LoginRequest, TokenResponse
from app.schemas.user_schema import UserCreate, UserPublic


router = APIRouter(prefix="/api/auth", tags=["Auth"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: UserCreate) -> TokenResponse:
    db = get_database()
    email = str(payload.email).lower()

    existing_user = await db.users.find_one({"email": email})
    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    user_doc = create_user_document(
        name=payload.name,
        email=email,
        password_hash=hash_password(payload.password),
        role=payload.role,
    )
    result = await db.users.insert_one(user_doc)
    user_doc["_id"] = result.inserted_id

    return TokenResponse(
        access_token=create_access_token(str(result.inserted_id)),
        user=user_to_public(user_doc),
    )


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest) -> TokenResponse:
    db = get_database()
    user = await db.users.find_one({"email": str(payload.email).lower()})

    if user is None or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    return TokenResponse(
        access_token=create_access_token(str(user["_id"])),
        user=user_to_public(user),
    )


@router.get("/me", response_model=UserPublic)
async def get_me(current_user: dict = Depends(get_current_user)) -> UserPublic:
    return user_to_public(current_user)
