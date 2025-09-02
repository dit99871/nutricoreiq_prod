from datetime import datetime
from annotated_types import MinLen, MaxLen
from pydantic import (
    AfterValidator,
    BeforeValidator,
    EmailStr,
    Field,
    SecretStr,
    model_validator,
)
from typing import Annotated, Literal, Optional

from .base import BaseSchema, FormSchema
from src.app.models.user import GoalType, KFALevel
from src.app.core.utils.validators import (
    coerce_goal,
    coerce_kfa,
    validate_password_strength,
)
from src.app.core.constants import (
    MIN_AGE,
    MAX_AGE,
    MIN_HEIGHT_CM,
    MAX_HEIGHT_CM,
    MIN_WEIGHT_KG,
    MAX_WEIGHT_KG,
)


# базовая для input (create/update)
class UserBaseIn(FormSchema):
    username: Annotated[str, MinLen(3), MaxLen(20)]
    email: EmailStr


# базовая для output (read): сериализация, exclude sensitive
class UserBaseOut(BaseSchema):
    username: Annotated[str, MinLen(3), MaxLen(20)]
    email: EmailStr
    id: int
    uid: str


class UserCreate(UserBaseIn):
    """
    Схема для создания пользователя.
    """

    password: Annotated[
        SecretStr,
        MinLen(8),
        AfterValidator(validate_password_strength),
    ]


class UserPublic(UserBaseOut):
    """
    Публичная схема пользователя (output).
    """

    # исключаем из сериализации
    hashed_password: bytes | None = Field(default=None, exclude=True)


class UserProfile(UserBaseOut):
    """
    Профиль пользователя (output, для чтения).
    """

    gender: Literal["female", "male"] | None = None
    age: int | None = Field(default=None, ge=MIN_AGE, le=MAX_AGE)
    weight: float | None = Field(default=None, ge=MIN_WEIGHT_KG, le=MAX_WEIGHT_KG)
    height: float | None = Field(default=None, ge=MIN_HEIGHT_CM, le=MAX_HEIGHT_CM)
    kfa: Annotated[KFALevel | None, BeforeValidator(coerce_kfa)] = None
    goal: Annotated[GoalType | None, BeforeValidator(coerce_goal)] = None
    created_at: datetime
    is_subscribed: bool


class UserProfileUpdate(FormSchema):
    """
    Схема для обновления профиля (input).
    """

    gender: Optional[Literal["female", "male"]] = None
    age: Optional[int] = Field(default=None, ge=MIN_AGE, le=MAX_AGE)
    weight: Optional[float] = Field(default=None, ge=MIN_WEIGHT_KG, le=MAX_WEIGHT_KG)
    height: Optional[float] = Field(default=None, ge=MIN_HEIGHT_CM, le=MAX_HEIGHT_CM)
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

    current_password: Annotated[str, MinLen(8)]
    new_password: Annotated[
        str,
        MinLen(8),
        AfterValidator(validate_password_strength),
    ]

    @model_validator(mode="after")
    def passwords_match(cls, values):
        if values.current_password == values.new_password:
            raise ValueError("Новый пароль должен отличаться от текущего")
        return values
