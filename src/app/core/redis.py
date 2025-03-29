from typing import Any, AsyncGenerator

from redis.asyncio import Redis

from core.config import settings


async def get_redis() -> AsyncGenerator[Any, Redis]:
    redis = Redis.from_url(
        url=settings.redis.url,
        decode_responses=True,
        socket_timeout=5,
        socket_connect_timeout=5,
    )
    try:
        yield redis
    finally:
        await redis.close()
