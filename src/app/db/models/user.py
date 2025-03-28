import datetime as dt
from datetime import datetime

from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from .mixins import IntIdPkMixin
from .base import Base


class User(IntIdPkMixin, Base):
    username: Mapped[str] = mapped_column(unique=True, index=True)
    email: Mapped[str] = mapped_column(unique=True, index=True)
    hashed_password: Mapped[bytes]
    gender: Mapped[str | None] = mapped_column(nullable=True)
    age: Mapped[int | None] = mapped_column(nullable=True)
    weight: Mapped[float | None] = mapped_column(nullable=True)
    height: Mapped[int | None] = mapped_column(nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True)
    role: Mapped[str] = mapped_column(default="user")
    created_at: Mapped[str] = mapped_column(default=datetime.now(dt.UTC).isoformat())

    refresh_tokens: Mapped[list["UserRefreshToken"]] = relationship(
        back_populates="users",
        cascade="all, delete",
    )
