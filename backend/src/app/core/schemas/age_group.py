from pydantic import BaseModel
from .base import BaseSchema


class AgeGroupBase(BaseModel):
    age_group: str


class AgeGroupCreate(AgeGroupBase):
    pass


class AgeGroupRead(AgeGroupBase, BaseSchema):
    id: int
