from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.database.mongodb import get_database
from app.dependencies.auth_dependency import require_admin
from app.models.processing_log_model import log_to_public

router = APIRouter(prefix="/api/processing-logs", tags=["Processing Logs"])


@router.get("")
async def list_processing_logs(
    _: dict = Depends(require_admin),
    limit: int = Query(default=100, ge=1, le=500),
) -> list[dict[str, object]]:
    db = get_database()
    logs = (
        await db.processing_logs.find({})
        .sort("created_at", -1)
        .to_list(length=limit)
    )
    return [log_to_public(log) for log in logs]
