import datetime as dt
from typing import Literal
from uuid import uuid4

from sqlalchemy.orm import (
    Mapped,
    mapped_column,
)

from .mixins import IntIdPkMixin
from .base import Base


class User(IntIdPkMixin, Base):
    uid: Mapped[str] = mapped_column(default=str(uuid4()))
    username: Mapped[str] = mapped_column(unique=True, index=True)
    email: Mapped[str] = mapped_column(unique=True, index=True)
    hashed_password: Mapped[bytes]
    gender: Mapped[Literal["female", "male"] | None] = mapped_column(nullable=True)
    age: Mapped[int | None] = mapped_column(nullable=True)
    weight: Mapped[float | None] = mapped_column(nullable=True)
    height: Mapped[float | None] = mapped_column(nullable=True)

    is_active: Mapped[bool] = mapped_column(default=True)
    role: Mapped[str] = mapped_column(default="user")
    created_at: Mapped[str] = mapped_column(
        default=dt.datetime.now(dt.UTC).strftime("%Y-%m-%d %H:%M:%S")
    )
