from pydantic import BaseModel, ConfigDict
from datetime import datetime


class CustomBaseModel(BaseModel):
    """Глобальная базовая модель для всех схем с общей конфигурацией."""

    model_config = ConfigDict(
        from_attributes=True,  # поддержка orm
        populate_by_name=True,  # для алиасов полей
        json_encoders={
            datetime: lambda v: v.isoformat(),  # форматирование дат
            bytes: lambda v: (
                v.decode("utf-8") if v else None
            ),  # для байтовых полей (hashed_password)
        },
        arbitrary_types_allowed=True,  # для enum и кастомных типов
    )


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
