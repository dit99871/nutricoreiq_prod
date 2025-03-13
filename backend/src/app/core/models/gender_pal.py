from sqlalchemy import ForeignKey
from sqlalchemy.orm import mapped_column, Mapped, relationship

from core.models import Base
from core.models.mixins.int_id_pk import IntIdPkMixin


class GenderPAL(IntIdPkMixin, Base):
    age_group_id: Mapped[int] = mapped_column(ForeignKey("age_groups.id"))
    pal: Mapped[float] = mapped_column(nullable=False)
    energy: Mapped[float] = mapped_column(nullable=False)
    proteins: Mapped[float] = mapped_column(nullable=False)
    fats: Mapped[float] = mapped_column(nullable=False)
    carbohydrates: Mapped[float] = mapped_column(nullable=False)

    age_group = relationship("AgeGroup", back_populates="pal")


class MalePAL(GenderPAL):
    pass


class FemalePAL(GenderPAL):
    pass
