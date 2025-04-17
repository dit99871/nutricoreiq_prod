from enum import Enum

from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base
from .mixins.int_id_pk import IntIdPkMixin


class NutrientCategory(Enum):
    MACRO = "MACRO"
    ENERGY_VALUE = "ENERGY_VALUE"
    NONESSENTIAL_AMINO = "NONESSENTIAL_AMINO"
    ESSENTIAL_AMINO = "ESSENTIAL_AMINO"
    COND_ESSENTIAL_AMINO = "COND_ESSENTIAL_AMINO"
    SATURATED_FATS = "SATURATED_FATS"
    MONOUNSATURATED_FATS = "MONOUNSATURATED_FATS"
    POLYUNSATURATED_FATS = "POLYUNSATURATED_FATS"
    FATS = "FATS"
    CARBS = "CARBS"
    VITAMINS = "VITAMINS"
    VITAMIN_LIKE = "VITAMIN_LIKE"
    MINERALS_MACRO = "MINERALS_MACRO"
    MINERALS_MICRO = "MINERALS_MICRO"
    OTHER = "OTHER"


class Nutrient(IntIdPkMixin, Base):
    name: Mapped[str] = mapped_column(unique=True)
    unit: Mapped[str]
    category: Mapped[NutrientCategory] = mapped_column(default=NutrientCategory.OTHER)

    product_associations: Mapped[list["ProductNutrient"]] = relationship(
        back_populates="nutrients"
    )
