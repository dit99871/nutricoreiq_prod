from typing import AsyncGenerator, Any
from redis.asyncio import Redis
from src.app.core.config import settings
from src.app.core.logger import get_logger

log = get_logger("redis_core")


async def get_redis() -> AsyncGenerator[Any, Redis]:
    """
    Yields a Redis connection object after establishing a connection
    and closes the connection when done.

    The connection is configured with the following settings:
    - `decode_responses=True` - to decode responses from Redis as strings
    - `socket_timeout=5` - to set the socket timeout to 5 seconds
    - `socket_connect_timeout=5` - to set the socket connect timeout to 5 seconds

    The Redis connection is established from the Redis URL found in
    the `settings.redis.url` setting.

    :return: A Redis connection object
    :rtype: AsyncGenerator[Any, Redis]
    """
    redis = Redis.from_url(
        url=settings.redis.url,
        decode_responses=True,
        socket_timeout=5,
        socket_connect_timeout=5,
    )
    async with redis.client() as redis:
        try:
            log.info("Redis connection opening")
            yield redis
        finally:
            await redis.aclose()

        log.info("Redis connection closed")
