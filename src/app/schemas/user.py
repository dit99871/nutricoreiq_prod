from datetime import datetime
from typing import Annotated, Literal, Optional

from annotated_types import MaxLen, MinLen
from pydantic import (
    AfterValidator,
    BeforeValidator,
    EmailStr,
    Field,
    constr,
    model_validator,
)

from src.app.core.constants import (
    MAX_AGE,
    MAX_HEIGHT_CM,
    MAX_WEIGHT_KG,
    MIN_AGE,
    MIN_HEIGHT_CM,
    MIN_WEIGHT_KG,
)
from src.app.core.utils.validators import (
    coerce_goal,
    coerce_kfa,
    validate_password_strength,
)
from src.app.models.user import GoalType, KFALevel

from .base import BaseSchema, FormSchema


# базовая для input (create/update)
class UserBaseIn(FormSchema):
    username: Annotated[str, MinLen(3), MaxLen(20)]
    email: EmailStr


# базовая для output (read): сериализация, exclude sensitive
class UserBaseOut(BaseSchema):
    username: Annotated[str, Field(min_length=3, max_length=20)]
    email: EmailStr
    id: int
    uid: str


class UserCreate(UserBaseIn):
    """
    Схема для создания пользователя.
    """

    password: Annotated[
        str,
        constr(min_length=8),
        AfterValidator(validate_password_strength),
    ]


class UserPublic(UserBaseOut):
    """
    Публичная схема пользователя (output).
    """

    # исключаем из сериализации
    hashed_password: Annotated[bytes | None, Field(exclude=True)] = None


class UserProfile(UserBaseOut):
    """
    Профиль пользователя (output, для чтения).
    """

    gender: Literal["female", "male"] | None = None
    age: Annotated[int | None, Field(ge=MIN_AGE, le=MAX_AGE)] = None
    weight: Annotated[float | None, Field(ge=MIN_WEIGHT_KG, le=MAX_WEIGHT_KG)] = None
    height: Annotated[float | None, Field(ge=MIN_HEIGHT_CM, le=MAX_HEIGHT_CM)] = None
    kfa: Annotated[KFALevel | None, BeforeValidator(coerce_kfa)] = None
    goal: Annotated[GoalType | None, BeforeValidator(coerce_goal)] = None
    created_at: datetime
    is_subscribed: bool


class UserProfileUpdate(FormSchema):
    """
    Схема для обновления профиля (input).
    """

    gender: Optional[Literal["female", "male"]] = None
    age: Annotated[int | None, Field(ge=MIN_AGE, le=MAX_AGE)] = None
    weight: Annotated[float | None, Field(ge=MIN_WEIGHT_KG, le=MAX_WEIGHT_KG)] = None
    height: Annotated[float | None, Field(ge=MIN_HEIGHT_CM, le=MAX_HEIGHT_CM)] = None
    kfa: Annotated[Optional[KFALevel], BeforeValidator(coerce_kfa)] = None
    goal: Annotated[Optional[GoalType], BeforeValidator(coerce_goal)] = None

    @model_validator(mode="after")
    def check_consistency(cls, values):
        # кросс-валидация (например, если age указан, проверить weight)
        if values.age is not None and values.weight is None:
            raise ValueError("Если указан возраст, укажите вес для полноты профиля")
        return values


class PasswordChange(FormSchema):
    """
    Схема для смены пароля.
    """

    current_password: Annotated[str, Field(min_length=8)]
    new_password: Annotated[
        str,
        MinLen(8),
        AfterValidator(validate_password_strength),
    ]

    @model_validator(mode="after")
    def passwords_match(self) -> "PasswordChange":
        # Получаем строковое представление паролей
        current = self.current_password
        new = (
            self.new_password.get_secret_value()
            if hasattr(self.new_password, "get_secret_value")
            else self.new_password
        )

        # Проверка на совпадение паролей
        if current == new:
            raise ValueError("Новый пароль должен отличаться от текущего")

        # Дополнительные проверки сложности пароля
        if not any(c.isupper() for c in new):
            raise ValueError("Пароль должен содержать хотя бы одну заглавную букву")
        if not any(c.islower() for c in new):
            raise ValueError("Пароль должен содержать хотя бы одну строчную букву")
        if not any(c.isdigit() for c in new):
            raise ValueError("Пароль должен содержать хотя бы одну цифру")

        return self
