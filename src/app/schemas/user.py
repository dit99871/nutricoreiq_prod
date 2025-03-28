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
    """
    Represents the response schema for a user.

    Inherits from UserBase and includes an optional hashed_password field.
    This class is used to structure the user data returned in responses.

    Attributes:
        hashed_password (bytes | None): The hashed password of the user, which is optional in responses.
    """

    hashed_password: bytes | None = None


class UserProfile(UserBase):
    gender: Literal["female", "male"]
    age: int
    weight: float
    height: int

    model_config = ConfigDict(strict=True)
