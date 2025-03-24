from typing import Annotated
from annotated_types import MaxLen, MinLen
from pydantic import EmailStr, ConfigDict

from .base import BaseSchema


class UserBase(BaseSchema):
    username: Annotated[str, MinLen(3), MaxLen(20)]
    email: EmailStr


class UserSchema(UserBase):
    hashed_password: bytes
    gender: str
    age: int
    weight: float
    role: str = "user"

    # model_config = ConfigDict(strict=True)
