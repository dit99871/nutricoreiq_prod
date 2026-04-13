"""ORM-модель группы продуктов."""

from __future__ import annotations
from typing import TYPE_CHECKING

from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base
from .mixins.int_id_pk import IntIdPkMixin

if TYPE_CHECKING:
    from .product import Product


class ProductGroup(IntIdPkMixin, Base):
    """Модель группы продуктов."""

    name: Mapped[str] = mapped_column(nullable=False)

    products: Mapped[list[Product]] = relationship(back_populates="product_groups")
