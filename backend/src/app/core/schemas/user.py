from pydantic import BaseModel, EmailStr, ConfigDict
from datetime import datetime


class UserBase(BaseModel):
    username: str
    email: EmailStr
    gender: str
    age: int
    weight: float


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    username: str | None = None
    email: EmailStr | None = None
    gender: str | None = None
    age: int | None = None
    weight: float | None = None


class UserRead(UserBase):
    id: int
    is_active: bool
    is_admin: bool

    model_config = ConfigDict(
        from_attributes=True,
    )


class UserDelete(UserBase):
    id: int
    is_active: bool
    is_admin: bool
    deleted_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
    )


class DeletedUser(UserBase):
    id: int
    is_active: bool
    is_admin: bool
    deleted_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
    )
