from pydantic import BaseModel
from .base import BaseSchema


class NutrientBase(BaseModel):
    name: str


class NutrientCreate(NutrientBase):
    pass


class NutrientRead(NutrientBase, BaseSchema):
    id: int
