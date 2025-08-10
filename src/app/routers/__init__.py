from fastapi import APIRouter

from src.app.core.config import settings
from src.app.routers.auth import router as auth_router
from src.app.routers.info import router as info_router
from src.app.routers.product import router as product_router
from src.app.routers.security import router as security_router
from src.app.routers.user import router as users_router

routers = APIRouter()

routers.include_router(
    auth_router,
    prefix=settings.router.auth,
)
routers.include_router(
    product_router,
    prefix=settings.router.product,
)
routers.include_router(
    security_router,
    prefix=settings.router.security,
)
routers.include_router(
    users_router,
    prefix=settings.router.user,
)
routers.include_router(
    info_router,
)
