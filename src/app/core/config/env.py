"""Настройки окружения (dev/test/prod)."""

from pydantic import BaseModel


class EnvConfig(BaseModel):
    """Конфигурация типа окружения приложения."""

    env: str = "dev"
