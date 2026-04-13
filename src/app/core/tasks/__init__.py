"""Пакет фоновых задач Taskiq."""

__all__ = ("send_welcome_email", "send_event_to_loki")

from .welcome_email_notification import send_welcome_email
from .sentry_task import send_event_to_loki
