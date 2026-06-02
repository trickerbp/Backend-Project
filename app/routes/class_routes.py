from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pymongo import ReturnDocument

from app.database.mongodb import get_database
from app.dependencies.auth_dependency import get_current_user, require_admin
from app.models.class_model import create_class_document, class_to_response
from app.schemas.class_schema import ClassCreate, ClassResponse, ClassUpdate
from app.utils.objectid import to_object_id


router = APIRouter(prefix="/api/classes", tags=["Classes"])


@router.get("", response_model=list[ClassResponse])
async def list_classes(
    search: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    current_user: dict = Depends(get_current_user),
) -> list[ClassResponse]:
    db = get_database()
    query = {}

    if search:
        query["$or"] = [
            {"class_name": {"$regex": search, "$options": "i"}},
            {"teacher_name": {"$regex": search, "$options": "i"}},
            {"room": {"$regex": search, "$options": "i"}},
        ]

    if status_filter:
        if status_filter not in {"open", "closed"}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid class status",
            )
        query["status"] = status_filter

    classes = await db.classes.find(query).sort("created_at", -1).to_list(length=None)
    return [class_to_response(class_doc) for class_doc in classes]


@router.get("/{class_id}", response_model=ClassResponse)
async def get_class(
    class_id: str,
    current_user: dict = Depends(get_current_user),
) -> ClassResponse:
    db = get_database()
    class_doc = await db.classes.find_one({"_id": to_object_id(class_id, "class_id")})

    if class_doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Class not found",
        )

    return class_to_response(class_doc)


@router.post("", response_model=ClassResponse, status_code=status.HTTP_201_CREATED)
async def create_class(
    payload: ClassCreate,
    current_user: dict = Depends(require_admin),
) -> ClassResponse:
    db = get_database()
    class_doc = create_class_document(
        class_data=payload.model_dump(),
        created_by=current_user["_id"],
    )
    result = await db.classes.insert_one(class_doc)
    class_doc["_id"] = result.inserted_id
    return class_to_response(class_doc)


@router.put("/{class_id}", response_model=ClassResponse)
async def update_class(
    class_id: str,
    payload: ClassUpdate,
    current_user: dict = Depends(require_admin),
) -> ClassResponse:
    db = get_database()
    class_object_id = to_object_id(class_id, "class_id")
    existing_class = await db.classes.find_one({"_id": class_object_id})

    if existing_class is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Class not found",
        )

    update_data = payload.model_dump(exclude_unset=True, exclude_none=True)
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No update data provided",
        )

    next_current_students = update_data.get(
        "current_students",
        existing_class.get("current_students", 0),
    )
    next_max_students = update_data.get("max_students", existing_class["max_students"])

    if next_current_students > next_max_students:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="current_students cannot be greater than max_students",
        )

    update_data["updated_at"] = datetime.now(timezone.utc)
    updated_class = await db.classes.find_one_and_update(
        {"_id": class_object_id},
        {"$set": update_data},
        return_document=ReturnDocument.AFTER,
    )

    return class_to_response(updated_class)


@router.delete("/{class_id}", status_code=status.HTTP_200_OK)
async def delete_class(
    class_id: str,
    current_user: dict = Depends(require_admin),
) -> dict[str, str]:
    db = get_database()
    result = await db.classes.delete_one({"_id": to_object_id(class_id, "class_id")})

    if result.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Class not found",
        )

    return {"message": "Class deleted successfully"}
