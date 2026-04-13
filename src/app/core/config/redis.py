"""Настройки Redis."""

from pydantic import BaseModel


class RedisConfig(BaseModel):
    """Конфигурация подключения и параметров Redis."""

    url: str
    salt: str
    password: str
    session_ttl: int
