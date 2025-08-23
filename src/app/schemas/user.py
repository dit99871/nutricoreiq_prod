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

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        # минимальные требования: буква в верхнем и нижнем регистре, цифра и спецсимвол
        has_lower = any(c.islower() for c in v)
        has_upper = any(c.isupper() for c in v)
        has_digit = any(c.isdigit() for c in v)
        has_special = any(not c.isalnum() for c in v)
        if not (has_lower and has_upper and has_digit and has_special):
            raise ValueError(
                "Пароль должен содержать строчные и прописные буквы, цифры и спецсимволы"
            )
        return v


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
    # все поля опциональны, строгие типы для переданных значений
    gender: Literal["female", "male"] | None = None
    age: int | None = Field(default=None, gt=0)
    weight: float | None = Field(default=None, gt=0)
    height: float | None = Field(default=None, gt=0)
    kfa: Literal["1", "2", "3", "4", "5"] | None = None
    goal: Literal["Снижение веса", "Увеличение веса", "Поддержание веса"] | None = None

    model_config = ConfigDict(strict=True)

    # пре-валидатор: "" -> None, "1"/1 -> KFALevel, уже Enum -> как есть
    @field_validator("kfa", mode="before")
    @classmethod
    def _coerce_kfa(cls, v):
        if v in (None, ""):
            return None
        if isinstance(v, KFALevel):
            return v
        s = str(v)
        for m in KFALevel:
            if m.value == s:
                return m
        raise ValueError(f"Недопустимое значение kfa: {v}")

    # Пре-валидатор: "" -> None, "Снижение веса" -> GoalType, уже Enum -> как есть
    @field_validator("goal", mode="before")
    @classmethod
    def _coerce_goal(cls, v):
        if v in (None, ""):
            return None
        if isinstance(v, GoalType):
            return v
        try:
            return GoalType(v)
        except Exception:
            raise ValueError(f"Недопустимое значение goal: {v}")


class PasswordChange(BaseSchema):
    current_password: Annotated[str, MinLen(8)]
    new_password: Annotated[str, MinLen(8)]
