from fastapi import APIRouter

from src.app.core.logger import get_logger

router = APIRouter()

log = get_logger("debug_router")


@router.get("/sentry-debug")
async def trigger_error():
    division_by_zero = 1 / 0
