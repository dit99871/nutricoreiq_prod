from sqlalchemy import ForeignKey
from sqlalchemy.orm import mapped_column, Mapped, relationship

from core.models import Base
from core.models.mixins.int_id_pk import IntIdPkMixin


class GenderMetabolism(IntIdPkMixin, Base):
    age_group_id: Mapped[int] = mapped_column(ForeignKey("age_groups.id"))
    weight: Mapped[float] = mapped_column(nullable=False)
    metabolism: Mapped[float] = mapped_column(nullable=False)

    age_group = relationship("AgeGroup", back_populates="metabolism")


class MaleMetabolism(GenderMetabolism):
    pass


class FemaleMetabolism(GenderMetabolism):
    pass
