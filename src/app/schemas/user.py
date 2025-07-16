from annotated_types import MinLen, MaxLen
from pydantic import ConfigDict, EmailStr, Field
from typing import Annotated, Literal

from .base import BaseSchema


class UserBase(BaseSchema):
    username: Annotated[str, MinLen(3), MaxLen(20)]
    email: EmailStr


class UserCreate(UserBase):
    password: Annotated[str, MinLen(8)]


class UserResponse(UserBase):
    id: int
    uid: str
    hashed_password: bytes | None = None


class UserAccount(UserBase):
    gender: Literal["female", "male"] | None
    age: int | None
    weight: float | None
    height: float | None
    kfa: str | None
    goal: str = Literal["Снижение веса", "Увеличение веса", "Поддержание веса"] | None
    created_at: str


class UserProfile(BaseSchema):
    gender: Literal["female", "male"]
    age: int = Field(gt=0)
    weight: float = Field(gt=0)
    height: float = Field(gt=0)
    kfa: str = Literal["1", "2", "3", "4", "5"]
    goal: str = Literal["Снижение веса", "Увеличение веса", "Поддержание веса"]

    model_config = ConfigDict(strict=True)


class PasswordChange(BaseSchema):
    current_password: Annotated[str, MinLen(8)]
    new_password: Annotated[str, MinLen(8)]
