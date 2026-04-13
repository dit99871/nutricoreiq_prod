"""Настройки кеширования."""

from pydantic import BaseModel


class CacheConfig(BaseModel):
    """Конфигурация TTL и параметров кеша."""

    user_ttl: int
    consent_ttl: int = 3600
