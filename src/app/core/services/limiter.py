from slowapi import Limiter
from slowapi.util import get_remote_address

from src.app.core.config.settings import settings

storage_uri = (
    settings.rate_limit.storage_uri or settings.redis.url
)  # e.g., "redis://redis:6379/0"
limiter = Limiter(
    key_func=get_remote_address,  # Default: по IP
    default_limits=["1000/hour"],  # Глобальный, если нужно (дополняет Nginx)
    storage_uri=storage_uri,
    strategy="fixed-window",  # Для точности с Redis
)
