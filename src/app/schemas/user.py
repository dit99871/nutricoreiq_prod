from datetime import datetime

from annotated_types import MinLen, MaxLen
from pydantic import ConfigDict, EmailStr, Field
from typing import Annotated, Literal

from .base import BaseSchema
from src.app.models.user import GoalType, KFALevel


class UserBase(BaseSchema):
    username: Annotated[str, MinLen(3), MaxLen(20)]
    email: EmailStr
    is_subscribed: bool = True


class UserCreate(UserBase):
    password: Annotated[str, MinLen(8)]


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


class UserProfile(BaseSchema):
    gender: Literal["female", "male"] = None
    age: int = Field(gt=0)
    weight: float = Field(gt=0)
    height: float = Field(gt=0)
    kfa: Literal["1", "2", "3", "4", "5"] = None
    goal: Literal["Снижение веса", "Увеличение веса", "Поддержание веса"] = None

    model_config = ConfigDict(strict=True)


class PasswordChange(BaseSchema):
    current_password: Annotated[str, MinLen(8)]
    new_password: Annotated[str, MinLen(8)]
