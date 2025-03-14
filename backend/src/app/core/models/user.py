from datetime import datetime

from sqlalchemy.orm import Mapped, mapped_column

from .base import Base
from .mixins.int_id_pk import IntIdPkMixin


class User(IntIdPkMixin, Base):
    username: Mapped[str] = mapped_column(unique=True, index=True)
    email: Mapped[str] = mapped_column(unique=True, index=True)
    hashed_password: Mapped[str]
    gender: Mapped[str]
    age: Mapped[int]
    weight: Mapped[float]
    is_active: Mapped[bool] = mapped_column(default=True)
    is_admin: Mapped[bool] = mapped_column(default=False)


class DeletedUser(IntIdPkMixin, Base):
    __tablename__ = "deleted_users"

    username: Mapped[str]
    email: Mapped[str]
    hashed_password: Mapped[str]
    gender: Mapped[str]
    age: Mapped[int]
    weight: Mapped[float]
    is_active: Mapped[bool]
    is_admin: Mapped[bool]
    deleted_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
