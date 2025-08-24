from datetime import datetime

from annotated_types import MinLen, MaxLen
from pydantic import ConfigDict, EmailStr, Field, BeforeValidator, AfterValidator
from typing import Annotated, Literal

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


class UserBase(BaseSchema):
    username: Annotated[str, MinLen(3), MaxLen(20)]
    email: EmailStr
    is_subscribed: bool = True


class UserCreate(UserBase):
    password: Annotated[
        str,
        MinLen(8),
        AfterValidator(validate_password_strength),
    ]


class UserResponse(UserBase):
    id: int
    uid: str
    # хранится в pydantic-модели для внутреннего использования (аутентификация),
    # но исключается из сериализации ответов/схем OpenAPI
    hashed_password: bytes | None = Field(default=None, exclude=True)


class UserPublic(BaseSchema):
    id: int
    uid: str
    username: Annotated[str, MinLen(3), MaxLen(20)]
    email: EmailStr
    is_subscribed: bool


class UserAccount(UserBase):
    gender: Literal["female", "male"] | None = None
    age: int | None
    weight: float | None
    height: float | None
    kfa: KFALevel | None
    goal: GoalType | None
    created_at: datetime


class UserProfile(FormSchema):
    # все поля опциональны, строгие типы для переданных значений
    gender: Literal["female", "male"] | None = None
    age: int | None = Field(default=None, ge=MIN_AGE, le=MAX_AGE)
    weight: float | None = Field(default=None, ge=MIN_WEIGHT_KG, le=MAX_WEIGHT_KG)
    height: float | None = Field(default=None, ge=MIN_HEIGHT_CM, le=MAX_HEIGHT_CM)
    kfa: Annotated[KFALevel | None, BeforeValidator(coerce_kfa)] = None
    goal: Annotated[GoalType | None, BeforeValidator(coerce_goal)] = None

    model_config = ConfigDict(
        from_attributes=True,
        use_enum_values=True,
        extra="forbid",  # запрещаем лишние поля, кроме унаследованных от FormSchema
    )


class PasswordChange(BaseSchema):
    current_password: Annotated[str, MinLen(8)]
    new_password: Annotated[
        str,
        MinLen(8),
        AfterValidator(validate_password_strength),
    ]
