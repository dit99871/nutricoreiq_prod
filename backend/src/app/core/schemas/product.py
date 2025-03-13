from pydantic import BaseModel
from .base import BaseSchema


class ProductBase(BaseModel):
    title: str
    group_id: int


class ProductCreate(ProductBase):
    pass


class ProductRead(ProductBase, BaseSchema):
    id: int
