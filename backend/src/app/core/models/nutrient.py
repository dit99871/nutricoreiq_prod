from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.models import Base
from core.models.mixins.int_id_pk import IntIdPkMixin


class Nutrient(IntIdPkMixin, Base):
    name: Mapped[str] = mapped_column(unique=True)

    products = relationship("ProductNutrient", back_populates="nutrient")
