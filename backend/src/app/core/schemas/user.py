from typing import Optional

from pydantic import BaseModel, EmailStr
from pydantic import ConfigDict


class UserBase(BaseModel):
    username: str
    email: EmailStr


class UserCreate(UserBase):
    gender: str
    age: int
    password: str
    weight: float


class UserRead(UserBase):
    id: int

    model_config = ConfigDict(
        from_attributes=True,
    )


class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    gender: Optional[str] = None
    age: Optional[int] = None
    weight: Optional[float] = None


class UserResponse(BaseModel):
    status: str
    user: UserRead
