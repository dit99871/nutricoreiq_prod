from pydantic import BaseModel
from pydantic import ConfigDict


class UserBase(BaseModel):
    username: str


class UserCreate(UserBase):
    email: str
    password: str
    gender: str
    age: int


class UserRead(UserBase):
    model_config = ConfigDict(
        from_attributes=True,
    )

    id: int
