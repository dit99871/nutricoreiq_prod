from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base
from .mixins.int_id_pk import IntIdPkMixin


class Nutrient(IntIdPkMixin, Base):
    name: Mapped[str] = mapped_column(unique=True)

    products: Mapped[list["ProductNutrient"]] = relationship(back_populates="nutrient")
