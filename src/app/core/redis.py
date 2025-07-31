from typing import AsyncGenerator, Any

from redis.asyncio import Redis

from src.app.core.config import settings
from src.app.core.logger import get_logger

log = get_logger("redis_core")

redis_client = Redis.from_url(
    url=str(settings.redis.url),
    decode_responses=True,
    socket_timeout=5,
    socket_connect_timeout=5,
)


async def get_redis() -> AsyncGenerator[Any, Redis]:
    """
    Yields a Redis connection object for dependency injection.
    """
    async with redis_client.client() as redis:
        try:
            yield redis
        finally:
            await redis.aclose()


async def init_redis():
    """
    Initialize Redis connection at application startup.
    """
    await redis_client.ping()
    # log.info("Redis connection established")


async def close_redis():
    """
    Close Redis connection at application shutdown.
    """
    await redis_client.aclose()
    # log.info("Redis connection closed")
