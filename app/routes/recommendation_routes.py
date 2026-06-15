from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.database.mongodb import get_database
from app.dependencies.auth_dependency import require_student
from app.models.recommendation_model import recommendation_to_public
from app.schemas.recommendation_schema import (
    GenerateRecommendationRequest,
    RecommendationResponse,
)
from app.services import recommendation_service
from app.utils.objectid import to_object_id


router = APIRouter(prefix="/api/recommendations", tags=["Recommendations"])


@router.post("/generate", response_model=RecommendationResponse, status_code=status.HTTP_201_CREATED)
async def generate(
    payload: GenerateRecommendationRequest | None = None,
    current_user: dict = Depends(require_student),
) -> RecommendationResponse:
    db = get_database()

    if payload is not None and payload.student_profile_id:
        oid = to_object_id(payload.student_profile_id, "student_profile_id")
        profile = await db.student_profiles.find_one(
            {"_id": oid, "student_id": current_user["_id"]}
        )
    else:
        profiles = (
            await db.student_profiles.find({"student_id": current_user["_id"]})
            .sort("created_at", -1)
            .to_list(length=1)
        )
        profile = profiles[0] if profiles else None

    if profile is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "No student profile found. Create a profile first.",
        )

    document = await recommendation_service.generate_recommendations(
        db, current_user["_id"], profile
    )
    return recommendation_to_public(document)


@router.get("/me", response_model=list[RecommendationResponse])
async def list_my_recommendations(
    current_user: dict = Depends(require_student),
) -> list[RecommendationResponse]:
    db = get_database()
    docs = (
        await db.recommendations.find({"student_id": current_user["_id"]})
        .sort("created_at", -1)
        .to_list(length=None)
    )
    return [recommendation_to_public(doc) for doc in docs]
