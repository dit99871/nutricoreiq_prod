from sqlalchemy.orm import mapped_column, Mapped, relationship

from .base import Base
from .mixins.int_id_pk import IntIdPkMixin


class AgeGroup(IntIdPkMixin, Base):
    age_group: Mapped[str] = mapped_column(nullable=False)

    metabolism = relationship("MaleMetabolism", back_populates="age_group")
    pal = relationship("MalePAL", back_populates="age_group")
    nutrients = relationship("MaleAgeSpecificNutrients", back_populates="age_group")
