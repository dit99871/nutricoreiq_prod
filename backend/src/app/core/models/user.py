from sqlalchemy.orm import Mapped, mapped_column

from core.models import Base
from core.models.mixins.int_id_pk import IntIdPkMixin


class User(IntIdPkMixin, Base):
    username: Mapped[str] = mapped_column(unique=True, index=True)
    email: Mapped[str] = mapped_column(unique=True, index=True)
    password: Mapped[str]
    gender: Mapped[str]
    age: Mapped[int]
