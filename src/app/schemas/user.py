from annotated_types import MinLen, MaxLen
from pydantic import ConfigDict, EmailStr, Field
from typing import Annotated, Literal, Optional

from .base import BaseSchema


class UserBase(BaseSchema):
    username: str = Field(..., min_length=3, max_length=20)
    email: EmailStr
    hashed_password: Optional[bytes]
    gender: Optional[str] = Field(pattern="^(female|male)?$")
    age: Optional[int]
    weight: Optional[float]
    height: Optional[float]
    created_at: str


class UserCreate(UserBase):
    password: Annotated[str, MinLen(8)]


class UserResponse(BaseSchema):
    id: int
    uid: str
    username: Annotated[str, MinLen(3), MaxLen(20)]
    email: EmailStr
    hashed_password: bytes | None = None


class UserProfile(BaseSchema):
    gender: Literal["female", "male"]
    age: int = Field(gt=0)
    weight: float = Field(gt=0)
    height: float = Field(gt=0)
    created_at: str

    model_config = ConfigDict(strict=True)
