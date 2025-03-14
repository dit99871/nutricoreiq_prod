from typing import Optional

from pydantic import BaseModel, EmailStr

from .base import BaseSchema


class UserBase(BaseModel):
    username: str


class UserCreate(UserBase):
    age: int
    gender: str
    email: EmailStr
    password: str
    weight: float


class UserRead(UserBase, BaseSchema):
    id: int
    is_active: bool
    is_admin: bool


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
