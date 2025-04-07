from fastapi import APIRouter

from core.config import settings
from .auth import router as auth_router
from .product import router as product_router
from .user import router as users_router

router = APIRouter(
    prefix=settings.api.v1.prefix,
)
router.include_router(
    auth_router,
    prefix=settings.api.v1.auth,
)
router.include_router(product_router, prefix=settings.api.v1.product)
router.include_router(
    users_router,
    prefix=settings.api.v1.user,
)
