from typing import Annotated, Literal
from annotated_types import MaxLen, MinLen
from pydantic import EmailStr, ConfigDict, field_validator

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


class UserProfile(BaseSchema):
    gender: Literal["female", "male"]
    age: int
    weight: float | int
    height: float | int

    @field_validator("age", "height")
    def validate_positive_numbers(cls, v):
        if v <= 0:
            raise ValueError("Must be positive")
        return v

    model_config = ConfigDict(strict=True)
