"""ORM-модели согласий на обработку персональных данных."""

from __future__ import annotations
from typing import TYPE_CHECKING
import datetime
from enum import Enum

from sqlalchemy import ForeignKey, Index, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base
from .mixins.int_id_pk import IntIdPkMixin

if TYPE_CHECKING:
    from .user import User


class ConsentType(Enum):
    """Типы согласия на обработку персональных данных"""

    PERSONAL_DATA = "personal_data"  # согласие на обработку персональных данных
    COOKIES = "cookies"  # согласие на использование кук
    MARKETING = "marketing"  # согласие на маркетинговые коммуникации


class PrivacyConsent(IntIdPkMixin, Base):
    """Модель для хранения согласия на обработку персональных данных"""

    __table_args__ = (
        Index("idx_privacy_consent_user_id", "user_id"),
        Index("idx_privacy_consent_session_id", "session_id"),
        Index("idx_privacy_consent_type", "consent_type"),
    )

    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True
    )
    session_id: Mapped[str | None] = mapped_column(nullable=True, index=True)
    ip_address: Mapped[str] = mapped_column(nullable=False)
    user_agent: Mapped[str] = mapped_column(nullable=False)
    consent_type: Mapped[ConsentType] = mapped_column(nullable=False)
    # статус согласия
    is_granted: Mapped[bool] = mapped_column(nullable=False, default=True)
    # дата и время согласия
    granted_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
        nullable=False,
    )
    # текст политики конфиденциальности на момент согласия
    policy_version: Mapped[str] = mapped_column(nullable=False, default="1.0")

    user: Mapped[User] = relationship(
        "User", back_populates="privacy_consents", lazy="joined"
    )
