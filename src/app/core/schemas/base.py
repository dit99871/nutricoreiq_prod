"""Базовые схемы (Pydantic) и общие настройки сериализации."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, field_serializer


class CustomBaseModel(BaseModel):
    """Глобальная базовая модель для всех схем с общей конфигурацией."""

    model_config = ConfigDict(
        from_attributes=True,  # поддержка orm
        populate_by_name=True,  # для алиасов полей
        arbitrary_types_allowed=True,  # для enum и кастомных типов
    )

    @field_serializer("*", when_used="unless-none")
    def serialize_dates(self, value: Any, _info) -> Any:
        """Сериализация дат и байтов в JSON-совместимый формат."""

        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, bytes):
            return value.decode("utf-8") if value else None

        return value


class BaseSchema(CustomBaseModel):
    """
    Базовая схема для output (чтения/ответов).
    Используется для сериализации данных из ORM в API-ответы.
    """

    model_config = ConfigDict(
        from_attributes=True,
        use_enum_values=True,  # дамп .value для enum в ответах (для фронтенда)
        extra="forbid",  # запрещаем лишние поля для строгой сериализации
    )


class FormSchema(CustomBaseModel):
    """
    Базовая схема для форм (input) с CSRF-токеном.
    Подходит для входящих данных из форм, игнорирует лишние поля (например, CSRF).
    """

    _csrf_token: str | None = None

    model_config = ConfigDict(
        from_attributes=False,  # не нужно для input-данных
        use_enum_values=False,  # сохраняем enum-объекты для внутренних операций (круды)
        extra="ignore",  # игнорируем лишние поля (для форм с csrf)
    )
