
from app.routes.auth_routes import router as auth_router
from app.routes.class_routes import router as class_router
from app.routes.enrollment_routes import router as enrollment_router
from app.routes.user_routes import router as user_router


__all__ = [
    "auth_router",
    "class_router",
    "enrollment_router",
    "user_router",
]
