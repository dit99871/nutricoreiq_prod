"""Настройки Loki."""

from pydantic import BaseModel


class LokiConfig(BaseModel):
    """Конфигурация URL для отправки логов в Loki."""

    url: str | None = None
