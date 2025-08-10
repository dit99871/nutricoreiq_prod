from fastapi import APIRouter

from src.app.core.config import settings
from src.app.routers.v1 import router as router_api_v1

routers = APIRouter(
    prefix=settings.router.prefix,
)
routers.include_router(router_api_v1)
