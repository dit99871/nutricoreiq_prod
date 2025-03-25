from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base
from .mixins.int_id_pk import IntIdPkMixin


class Product(IntIdPkMixin, Base):
    title: Mapped[str] = mapped_column(nullable=False)

    group = relationship("ProductGroup", back_populates="products")
    nutrients = relationship("ProductNutrient", back_populates="products")
