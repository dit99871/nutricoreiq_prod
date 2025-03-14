from sqlalchemy import ForeignKey
from sqlalchemy.orm import mapped_column, Mapped, relationship

from .base import Base
from .mixins.int_id_pk import IntIdPkMixin


class GenderAgeSpecificNutrient(IntIdPkMixin, Base):
    age_group_id: Mapped[int] = mapped_column(ForeignKey("age_groups.id"))
    nutrient_id: Mapped[int] = mapped_column(ForeignKey("nutrients.id"))
    demand: Mapped[float] = mapped_column(nullable=False)

    age_group = relationship("AgeGroup", back_populates="nutrients")
    nutrient = relationship("Nutrient")


class MaleAgeSpecificNutrient(GenderAgeSpecificNutrient):
    pass


class FemaleAgeSpecificNutrient(GenderAgeSpecificNutrient):
    pass
