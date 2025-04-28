from sqlalchemy import ForeignKey, Index, event, DDL
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base
from .mixins.int_id_pk import IntIdPkMixin


class Product(IntIdPkMixin, Base):
    title: Mapped[str] = mapped_column(nullable=False)
    group_id: Mapped[int] = mapped_column(ForeignKey("product_groups.id"))

    search_vector: Mapped[TSVECTOR] = mapped_column(TSVECTOR())

    product_groups: Mapped["ProductGroup"] = relationship(
        back_populates="products", lazy="joined"
    )
    nutrient_associations: Mapped[list["ProductNutrient"]] = relationship(
        back_populates="products",
        lazy="selectin",
    )

    # Индексы
    __table_args__ = (
        Index(
            "idx_product_search_vector",
            search_vector,
            postgresql_using="gin",
        ),
        Index(
            "idx_product_title_trgm",
            title,
            postgresql_using="gin",
            postgresql_ops={"title": "gin_trgm_ops"},
        ),
    )
