from enum import Enum

from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base
from .mixins.int_id_pk import IntIdPkMixin


class NutrientCategory(Enum):
    MACRO = "macro"
    ENERGY_VALUE = "energy_value"
    NONESSENTIAL_AMINO = "nonessentional_amino"
    ESSENTIAL_AMINO = "essential_amino"
    COND_ESSENTIAL_AMINO = "cond_essential_amino"
    SATURATED_FATS = "saturated_fats"
    MONOUNSATURATED_FATS = "monounsaturated_fats"
    POLYUNSATURATED_FATS = "polyunsaturated_fats"
    FATS = "fats"
    CARBS = "carbs"
    VITAMINS = "vitamins"
    VITAMIN_LIKE = "vitamin_like"
    MINERALS_MACRO = "minerals_macro"
    MINERALS_MICRO = "minerals_micro"
    OTHER = "other"


class Nutrient(IntIdPkMixin, Base):
    name: Mapped[str] = mapped_column(unique=True)
    unit: Mapped[str]
    category: Mapped[NutrientCategory] = mapped_column(default=NutrientCategory.OTHER)

    product_associations: Mapped[list["ProductNutrient"]] = relationship(
        back_populates="nutrients"
    )
