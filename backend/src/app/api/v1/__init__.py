from fastapi import APIRouter

from .auth import router as auth_router
from core.config import settings
from .user import router as users_router

router = APIRouter(
    prefix=settings.api.v1.prefix,
)
router.include_router(
    users_router,
    prefix=settings.api.v1.user,
)
router.include_router(
    auth_router,
    prefix=settings.api.v1.auth,
)
