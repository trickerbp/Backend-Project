from app.schemas.auth_schema import LoginRequest, TokenResponse
from app.schemas.course_schema import CourseCreate, CourseResponse, CourseUpdate
from app.schemas.course_resource_schema import CourseResourceResponse
from app.schemas.recommendation_schema import (
    GenerateRecommendationRequest,
    RecommendationEventCreate,
    RecommendationResponse,
)
from app.schemas.student_profile_schema import (
    StudentProfileCreate,
    StudentProfileResponse,
    StudentProfileUpdate,
)
from app.schemas.user_schema import UserCreate, UserPublic


__all__ = [
    "CourseCreate",
    "CourseResponse",
    "CourseResourceResponse",
    "CourseUpdate",
    "GenerateRecommendationRequest",
    "LoginRequest",
    "RecommendationEventCreate",
    "RecommendationResponse",
    "StudentProfileCreate",
    "StudentProfileResponse",
    "StudentProfileUpdate",
    "TokenResponse",
    "UserCreate",
    "UserPublic",
]
