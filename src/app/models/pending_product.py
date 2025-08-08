import datetime as dt

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base
from .mixins.int_id_pk import IntIdPkMixin


class PendingProduct(Base, IntIdPkMixin):
    name: Mapped[str] = mapped_column(String(40), nullable=False)
    created_at: Mapped[str] = mapped_column(
        default=dt.datetime.now(dt.UTC).strftime("%Y-%m-%d %H:%M:%S")
    )
