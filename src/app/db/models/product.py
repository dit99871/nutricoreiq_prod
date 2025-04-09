from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base
from .mixins.int_id_pk import IntIdPkMixin


class Product(IntIdPkMixin, Base):
    title: Mapped[str] = mapped_column(nullable=False)
    group_id: Mapped[int] = mapped_column(ForeignKey("product_groups.id"))

    product_groups: Mapped["ProductGroup"] = relationship(back_populates="products")
    nutrient_associations: Mapped[list["ProductNutrient"]] = relationship(
        back_populates="products"
    )
