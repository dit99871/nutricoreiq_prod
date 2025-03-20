from sqlalchemy.orm import Mapped, mapped_column

from .mixins import IntIdPkMixin
from .base import Base


class User(IntIdPkMixin, Base):
    username: Mapped[str] = mapped_column(unique=True, index=True)
    email: Mapped[str] = mapped_column(unique=True, index=True)
    hashed_password: Mapped[bytes]
    gender: Mapped[str]
    age: Mapped[int]
    weight: Mapped[float]
    is_active: Mapped[bool] = mapped_column(default=True)
