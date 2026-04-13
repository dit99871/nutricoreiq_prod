"""Настройки запуска приложения."""

from pydantic import BaseModel


class RunConfig(BaseModel):
    """Конфигурация host/port и trusted proxies."""

    host: str
    port: int
    trusted_proxies: list[str] = []
