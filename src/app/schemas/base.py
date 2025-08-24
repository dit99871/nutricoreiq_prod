from pydantic import BaseModel, ConfigDict


class BaseSchema(BaseModel):

    model_config = ConfigDict(
        from_attributes=True,
        use_enum_values=True,
        extra="forbid",
    )


class FormSchema(BaseModel):
    """Базовая схема для форм с CSRF-токеном."""
    _csrf_token: str | None = None

    model_config = ConfigDict(
        from_attributes=True,
        use_enum_values=True,
        extra="ignore",  # Разрешаем игнорировать лишние поля, но не добавлять их в модель
    )
