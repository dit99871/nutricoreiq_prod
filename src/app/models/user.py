import datetime
from enum import Enum
from typing import Literal
from uuid import uuid4

from sqlalchemy.orm import Mapped, mapped_column

from .mixins import IntIdPkMixin
from .base import Base


class UserRole(Enum):
    USER = "user"
    ADMIN = "admin"
    MODERATOR = "moderator"


class KFALevel(Enum):
    VERY_LOW = "1"
    LOW = "2"
    MEDIUM = "3"
    HIGH = "4"
    VERY_HIGH = "5"


class GoalType(Enum):
    LOSE_WEIGHT = "Снижение веса"
    GAIN_WEIGHT = "Увеличение веса"
    MAINTAIN_WEIGHT = "Поддержание веса"


class User(IntIdPkMixin, Base):
    uid: Mapped[str] = mapped_column(
        unique=True, index=True, default=lambda: str(uuid4())
    )
    username: Mapped[str] = mapped_column(unique=True, index=True)
    email: Mapped[str] = mapped_column(unique=True, index=True)
    hashed_password: Mapped[bytes]

    gender: Mapped[Literal["female", "male"] | None] = mapped_column(nullable=True)
    age: Mapped[int | None] = mapped_column(nullable=True)
    weight: Mapped[float | None] = mapped_column(nullable=True)
    height: Mapped[float | None] = mapped_column(nullable=True)
    kfa: Mapped[KFALevel | None] = mapped_column(nullable=True)
    goal: Mapped[GoalType | None] = mapped_column(nullable=True)

    is_subscribed: Mapped[bool] = mapped_column(default=True)
    is_active: Mapped[bool] = mapped_column(default=True, index=True)
    role: Mapped[UserRole] = mapped_column(default=UserRole.USER)

    created_at: Mapped[datetime.datetime] = mapped_column(
        default=lambda: datetime.datetime.now().date(), index=True
    )
