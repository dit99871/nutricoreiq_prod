from datetime import datetime

from typing import Annotated, Optional
from annotated_types import MaxLen, MinLen
from pydantic import EmailStr, ConfigDict

from .base import BaseSchema


class UserBase(BaseSchema):
    username: Annotated[str, MinLen(3), MaxLen(20)]
    email: EmailStr
    gender: str
    age: int
    weight: float


class UserCreate(UserBase):
    password: Annotated[str, MinLen(8), MaxLen(20)]
    role: Optional[str] = None

    model_config = ConfigDict(
        from_attributes=True,
        strict=True,
    )


class UserUpdate(BaseSchema):
    username: Annotated[str, MinLen(3), MaxLen(20)] = None
    email: Optional[EmailStr] = None
    gender: Optional[str] = None
    age: Optional[int] = None
    weight: Optional[float] = None


class UserRead(UserBase):
    id: int
    is_active: bool
    role: str


class UserDelete(UserBase):
    id: int
    is_active: bool
    role: str
    deleted_at: datetime
