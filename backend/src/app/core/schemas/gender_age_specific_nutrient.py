from pydantic import BaseModel
from .base import BaseSchema


class GenderAgeSpecificNutrientsBase(BaseModel):
    age_group_id: int
    nutrient_id: int
    demand: float


class MaleAgeSpecificNutrientsCreate(GenderAgeSpecificNutrientsBase):
    pass


class MaleAgeSpecificNutrientsRead(GenderAgeSpecificNutrientsBase, BaseSchema):
    id: int


class FemaleAgeSpecificNutrientsCreate(GenderAgeSpecificNutrientsBase):
    pass


class FemaleAgeSpecificNutrientsRead(GenderAgeSpecificNutrientsBase, BaseSchema):
    id: int
