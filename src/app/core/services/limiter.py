"""Сервис для ограничения количества запросов."""

from slowapi import Limiter
from slowapi.util import get_remote_address

from src.app.core.config.settings import settings

storage_uri = (
    settings.rate_limit.storage_uri or settings.redis.url
)  # e.g., "redis://redis:6379/0"
limiter = Limiter(
    key_func=get_remote_address,  # по умолчанию: по ip
    default_limits=["1000/hour"],  # глобальный, если нужно (дополняет nginx)
    storage_uri=storage_uri,
    strategy="fixed-window",  # для точности с редисом
)
