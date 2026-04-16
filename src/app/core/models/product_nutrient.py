"""ORM-модель связи продукта и нутриента (таблица-ассоциация)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .nutrient import Nutrient
    from .product import Product


class ProductNutrient(Base):
    """Модель с количеством нутриента в продукте."""

    amount: Mapped[float] = mapped_column(default=0.0)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"),
        primary_key=True,
    )
    nutrient_id: Mapped[int] = mapped_column(
        ForeignKey("nutrients.id", ondelete="CASCADE"),
        primary_key=True,
    )

    products: Mapped[Product] = relationship(back_populates="nutrient_associations")
    nutrients: Mapped[Nutrient] = relationship(back_populates="product_associations")
