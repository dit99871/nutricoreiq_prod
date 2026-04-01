import json
from typing import Optional

from src.app.core.config import settings
from src.app.core.logger import get_logger
from src.app.core.redis import get_redis_service

log = get_logger("cache_service")


class CacheService:
    """Сервис для обработки операций кеширования Redis."""

    @staticmethod
    def _get_user_cache_key(uid: str) -> str:
        """Сгенерировать ключ кеша для данных пользователя."""

        return f"user:{uid}"

    @classmethod
    async def get_user(cls, uid: str) -> Optional[dict]:
        """
        Получить данные пользователя из кеша.

        :param uid: ID пользователя
        :return: Данные пользователя если найдены, иначе None
        """

        try:
            async for redis in get_redis_service():
                key = cls._get_user_cache_key(uid)
                data = await redis.get(key)
                if data:
                    log.debug("Данные пользователя %s получены из кеша", uid)
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
        Кешировать данные пользователя.

        :param uid: ID пользователя
        :param user_data: Данные пользователя для кеширования
        """

        try:
            async for redis in get_redis_service():
                key = cls._get_user_cache_key(uid)
                # сериализуем словарь в json-строку
                serialized_data = json.dumps(user_data, ensure_ascii=False)
                await redis.setex(
                    name=key,
                    time=settings.cache.user_ttl,
                    value=serialized_data,
                )
                log.debug("Данные пользователя %s сохранены в кеш", uid)

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
        Инвалидировать кеш для конкретного пользователя.

        :param uid: ID пользователя для инвалидации
        """

        try:
            async for redis in get_redis_service():
                key = cls._get_user_cache_key(uid)
                await redis.delete(key)

        except Exception as e:
            log.error(
                "Ошибка при инвалидации кеша пользователя: %s",
                e,
            )


class ConsentCacheService:
    """Кеш для согласий на обработку данных"""

    CONSENT_TTL = settings.cache.consent_ttl
    KEY_PREFIX = "consent"

    @classmethod
    def _key(cls, user_id: int) -> str:
        return f"{cls.KEY_PREFIX}:{user_id}"

    @classmethod
    async def get(cls, user_id: int) -> bool | None:
        """None означает cache miss — нужно идти в БД"""
        try:
            async for redis in get_redis_service():
                value = await redis.get(cls._key(user_id))
                if value is not None:
                    return value == b"1"
        except Exception as e:
            log.error("Ошибка чтения кеша согласия: %s", e)
        return None

    @classmethod
    async def set(cls, user_id: int, has_consent: bool) -> None:
        try:
            async for redis in get_redis_service():
                await redis.set(
                    cls._key(user_id),
                    "1" if has_consent else "0",
                    ex=cls.CONSENT_TTL,
                )
        except Exception as e:
            log.error("Ошибка записи кеша согласия: %s", e)

    @classmethod
    async def invalidate(cls, user_id: int) -> None:
        try:
            async for redis in get_redis_service():
                await redis.delete(cls._key(user_id))
        except Exception as e:
            log.error("Ошибка инвалидации кеша согласия: %s", e)
