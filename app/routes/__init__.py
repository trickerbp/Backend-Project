from app.routes.auth_routes import router as auth_router
from app.routes.course_routes import router as course_router
from app.routes.course_resource_routes import router as course_resource_router
from app.routes.recommendation_routes import router as recommendation_router
from app.routes.student_profile_routes import router as student_profile_router
from app.routes.user_routes import router as user_router


__all__ = [
    "auth_router",
    "course_router",
    "course_resource_router",
    "recommendation_router",
    "student_profile_router",
    'user_router',
]
