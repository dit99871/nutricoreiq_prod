from datetime import datetime

from typing import Annotated, Optional
from annotated_types import MaxLen, MinLen
from pydantic import BaseModel, EmailStr, ConfigDict


class UserBase(BaseModel):
    username: Annotated[str, MinLen(3), MaxLen(20)]
    email: EmailStr
    gender: str
    age: int
    weight: float


class UserCreate(UserBase):
    password: bytes

    model_config = ConfigDict(strict=True)


class UserUpdate(BaseModel):
    username: Annotated[str, MinLen(3), MaxLen(20)] = None
    email: Optional[EmailStr] = None
    gender: Optional[str] = None
    age: Optional[int] = None
    weight: Optional[float] = None


class UserRead(UserBase):
    id: int
    is_active: bool
    role: str

    model_config = ConfigDict(
        from_attributes=True,
    )


class UserDelete(UserBase):
    id: int
    is_active: bool
    role: str
    deleted_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
    )
