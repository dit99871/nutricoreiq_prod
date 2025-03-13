from pydantic import BaseModel
from .base import BaseSchema


class ProductGroupBase(BaseModel):
    name: str


class ProductGroupCreate(ProductGroupBase):
    pass


class ProductGroupRead(ProductGroupBase, BaseSchema):
    id: int
