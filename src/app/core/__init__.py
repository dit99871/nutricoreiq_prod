"""Ядро приложения: конфиг, БД, broker и общие зависимости."""

__all__ = (
    "broker",
    "db_helper",
    "settings",
    "templates",
)

from .config import settings
from .db_helper import db_helper
from .utils.templates import templates

# экспортируем broker всегда: в prod — реальный, иначе — заглушка
if settings.env.env == "prod":
    from src.app.core.services.taskiq_broker import broker
else:
    from src.app.core.services.dummy_broker import broker
