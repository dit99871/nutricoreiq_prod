from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.models import Base
from core.models.mixins.int_id_pk import IntIdPkMixin


class ProductGroup(IntIdPkMixin, Base):
    name: Mapped[str] = mapped_column(nullable=False)

    products = relationship("Product", back_populates="group")
