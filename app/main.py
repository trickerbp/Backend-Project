
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.database.mongodb import close_mongo_connection, connect_to_mongo
from app.routes import (
    auth_router,
    course_resource_router,
    course_router,
    recommendation_router,
    student_profile_router,
    user_router,
)


settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_to_mongo()
    yield
    await close_mongo_connection()


app = FastAPI(
    title=settings.app_name,
    description=(
        "RESTful API for EduMatch Resource Mapping — mapping courses to "
        "student learning needs based on course resources."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_origin_regex=settings.cors_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(course_router)
app.include_router(course_resource_router)
app.include_router(student_profile_router)
app.include_router(recommendation_router)
app.include_router(user_router)


@app.get("/", tags=["Health"])
async def health_check() -> dict[str, str]:
    return {
        "message": "EduMatch Resource Mapping API is running",
        "docs": "/docs",
    }
