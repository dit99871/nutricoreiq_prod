"""Настройки Sentry."""

from pydantic import BaseModel


class SentryConfig(BaseModel):
    """Конфигурация DSN для Sentry."""

    dsn: str | None = None
