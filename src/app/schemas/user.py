from typing import Annotated, Literal
from annotated_types import MaxLen, MinLen
from pydantic import EmailStr, ConfigDict

from .base import BaseSchema


class UserBase(BaseSchema):
    username: Annotated[str, MinLen(3), MaxLen(20)]
    email: EmailStr


class UserCreate(UserBase):
    password: Annotated[str, MinLen(8)]


class UserResponse(UserBase):
    id: int
    hashed_password: bytes | None = None


class UserProfile(UserBase):
    gender: Literal["female", "male"]
    age: int
    weight: float
    height: int

    model_config = ConfigDict(strict=True)
