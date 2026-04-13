"""Настройки лимитов на чувствительные операции."""

from pydantic import BaseModel


class RateLimitConfig(BaseModel):
    """Конфигурация лимитов на чувствительные операции."""

    register_limit: str = "5/minute"
    login_limit: str = "5/minute"
    password_change_limit: str = "3/minute"
    storage_uri: str | None = None  # переопределяет redis.url
