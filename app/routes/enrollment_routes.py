from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.database.mongodb import get_database
from app.dependencies.auth_dependency import require_admin, require_student
from app.models.enrollment_model import enrollment_to_response
from app.schemas.enrollment_schema import EnrollmentCreate, EnrollmentResponse
from app.services.enrollment_service import (
    approve_enrollment,
    create_enrollment,
    reject_enrollment,
)


router = APIRouter(prefix="/api/enrollments", tags=["Enrollments"])


@router.post("", response_model=EnrollmentResponse, status_code=status.HTTP_201_CREATED)
async def enroll_class(
    payload: EnrollmentCreate,
    current_user: dict = Depends(require_student),
) -> EnrollmentResponse:
    db = get_database()
    return await create_enrollment(db, current_user["_id"], payload)


@router.get("/me", response_model=list[EnrollmentResponse])
async def get_my_enrollments(
    current_user: dict = Depends(require_student),
) -> list[EnrollmentResponse]:
    db = get_database()
    enrollments = await db.enrollments.find(
        {"student_id": current_user["_id"]},
    ).sort("created_at", -1).to_list(length=None)

    return [enrollment_to_response(enrollment) for enrollment in enrollments]


@router.get("", response_model=list[EnrollmentResponse])
async def list_enrollments(
    status_filter: str | None = Query(default=None, alias="status"),
    current_user: dict = Depends(require_admin),
) -> list[EnrollmentResponse]:
    db = get_database()
    query = {}

    if status_filter:
        if status_filter not in {"pending", "approved", "rejected"}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid enrollment status",
            )
        query["status"] = status_filter

    enrollments = await db.enrollments.find(query).sort("created_at", -1).to_list(
        length=None,
    )
    return [enrollment_to_response(enrollment) for enrollment in enrollments]


@router.patch("/{enrollment_id}/approve", response_model=EnrollmentResponse)
async def approve_enrollment_route(
    enrollment_id: str,
    current_user: dict = Depends(require_admin),
) -> EnrollmentResponse:
    db = get_database()
    return await approve_enrollment(db, enrollment_id, current_user["_id"])


@router.patch("/{enrollment_id}/reject", response_model=EnrollmentResponse)
async def reject_enrollment_route(
    enrollment_id: str,
    current_user: dict = Depends(require_admin),
) -> EnrollmentResponse:
    db = get_database()
    return await reject_enrollment(db, enrollment_id, current_user["_id"])
