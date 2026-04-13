"""Инициализация и зависимости Redis для приложения."""

from typing import Any, AsyncGenerator

from redis.asyncio import Redis

from src.app.core.config import settings
from src.app.core.logger import get_logger

log = get_logger("redis_core")

redis_client = Redis.from_url(
    url=str(settings.redis.url),
    decode_responses=True,
    socket_timeout=5,
    socket_connect_timeout=5,
    max_connections=100,
    health_check_interval=30,
    retry_on_timeout=True,
    socket_keepalive=True,
)


async def get_redis_service() -> AsyncGenerator[Any, Redis]:
    """Предоставляет объект подключения Redis для внедрения зависимостей."""

    async with redis_client.client() as redis:
        try:
            yield redis
        finally:
            await redis.aclose()


async def init_redis():
    """Инициализирует подключение Redis при запуске приложения."""

    await redis_client.ping()


async def close_redis():
    """Закрывает подключение Redis при остановке приложения."""

    await redis_client.aclose()
