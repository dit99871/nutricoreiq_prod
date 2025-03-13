from pydantic import BaseModel
from .base import BaseSchema


class GenderMetabolismBase(BaseModel):
    age_group_id: int
    weight: float
    metabolism: float


class MaleMetabolismCreate(GenderMetabolismBase):
    pass


class MaleMetabolismRead(GenderMetabolismBase, BaseSchema):
    id: int


class FemaleMetabolismCreate(GenderMetabolismBase):
    pass


class FemaleMetabolismRead(GenderMetabolismBase, BaseSchema):
    id: int
