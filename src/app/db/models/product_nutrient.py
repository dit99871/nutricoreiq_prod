from sqlalchemy import ForeignKey
from sqlalchemy.orm import mapped_column, Mapped, relationship

from .base import Base
from .mixins.int_id_pk import IntIdPkMixin


class ProductNutrient(IntIdPkMixin, Base):
    amount: Mapped[float] = mapped_column(nullable=False)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id"),
        primary_key=True,
    )
    nutrient_id: Mapped[int] = mapped_column(
        ForeignKey("nutrients.id"),
        primary_key=True,
    )

    product: Mapped["Product"] = relationship(back_populates="nutrients")
    nutrient: Mapped["Nutrient"] = relationship(back_populates="products")
