import json
from typing import Optional

from src.app.core.config import settings
from src.app.core.redis import get_redis
from src.app.core.logger import get_logger

log = get_logger("cache_service")


class CacheService:
    """Service for handling Redis caching operations."""

    @staticmethod
    def _get_user_cache_key(uid: str) -> str:
        """Generate cache key for user data."""

        return f"user:{uid}"

    @classmethod
    async def get_user(cls, uid: str) -> Optional[dict]:
        """
        Get user data from cache.

        :param uid: User ID
        :return: User data if found, None otherwise
        """

        try:
            async for redis in get_redis():
                key = cls._get_user_cache_key(uid)
                data = await redis.get(key)
                if data:
                    log.info("Данные пользователя %s получены из кеша", uid)
                    return json.loads(data)

        except json.JSONDecodeError as e:
            log.error(
                "Ошибка десериализации данных пользователя %s: %s",
                uid,
                e,
            )

        except Exception as e:
            log.error(
                "Ошибка при получении пользователя из кеша: %s",
                e,
            )

    @classmethod
    async def set_user(cls, uid: str, user_data: dict) -> None:
        """
        Cache user data.

        :param uid: User ID
        :param user_data: User data to cache
        """

        try:
            async for redis in get_redis():
                key = cls._get_user_cache_key(uid)
                # сериализуем словарь в json-строку
                serialized_data = json.dumps(user_data, ensure_ascii=False)
                await redis.setex(
                    name=key,
                    time=settings.cache.user_ttl,
                    value=serialized_data,
                )
                log.info("Данные пользователя %s сохранены в кеш", uid)

        except (TypeError, OverflowError) as e:
            log.error(
                "Ошибка сериализации данных пользователя %s: %s",
                uid,
                e,
            )

        except Exception as e:
            log.error(
                "Ошибка при сохранении пользователя в кеш: %s",
                e,
            )

    @classmethod
    async def invalidate_user(cls, uid: str) -> None:
        """
        Invalidate cache for a specific user.

        :param uid: User ID to invalidate
        """

        try:
            async for redis in get_redis():
                key = cls._get_user_cache_key(uid)
                await redis.delete(key)

        except Exception as e:
            log.error(
                "Ошибка при инвалидации кеша пользователя: %s",
                e,
            )
