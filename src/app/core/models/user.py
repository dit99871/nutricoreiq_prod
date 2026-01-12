import datetime
from enum import Enum, IntEnum
from typing import Literal
from uuid import uuid4

from sqlalchemy import CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base
from .mixins import IntIdPkMixin


class UserRole(Enum):
    USER = "user"
    ADMIN = "admin"
    MODERATOR = "moderator"


class KFALevel(IntEnum):
    """Уровень физической активности (KFA - Коэффициент Физической Активности)"""

    VERY_LOW = 1
    LOW = 2
    MEDIUM = 3
    HIGH = 4
    VERY_HIGH = 5

    def __str__(self):
        names = {
            1: "Очень низкий",
            2: "Низкий",
            3: "Средний",
            4: "Высокий",
            5: "Очень высокий",
        }
        return names[self.value]


class GoalType(Enum):
    LOSE_WEIGHT = "Снижение веса"
    GAIN_WEIGHT = "Увеличение веса"
    MAINTAIN_WEIGHT = "Поддержание веса"


class User(IntIdPkMixin, Base):
    __table_args__ = (
        CheckConstraint(
            "age IS NULL OR (age >= 10 AND age <= 120)", name="ck_users_age_range"
        ),
        CheckConstraint(
            "height IS NULL OR (height >= 50 AND height <= 300)",
            name="ck_users_height_range",
        ),
        CheckConstraint(
            "weight IS NULL OR (weight >= 20 AND weight <= 400)",
            name="ck_users_weight_range",
        ),
    )

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
