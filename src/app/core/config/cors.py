"""Настройки CORS."""

from pydantic import BaseModel


class CORSConfig(BaseModel):
    """Конфигурация политик CORS для API."""

    allow_origins: list[str]
    allow_methods: list[str]
    allow_headers: list[str]
    allow_credentials: bool
