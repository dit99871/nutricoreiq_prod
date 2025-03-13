from pydantic import BaseModel
from .base import BaseSchema


class GenderPALBase(BaseModel):
    age_group_id: int
    pal: float
    energy: float
    proteins: float
    fats: float
    carbohydrates: float


class MalePALCreate(GenderPALBase):
    pass


class MalePALRead(GenderPALBase, BaseSchema):
    id: int


class FemalePALCreate(GenderPALBase):
    pass


class FemalePALRead(GenderPALBase, BaseSchema):
    id: int
