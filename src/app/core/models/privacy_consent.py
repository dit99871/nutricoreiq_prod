import datetime
from enum import Enum

from sqlalchemy import ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base
from .mixins.int_id_pk import IntIdPkMixin


class ConsentType(Enum):
    """Типы согласия на обработку персональных данных"""
    PERSONAL_DATA = "personal_data"  # Согласие на обработку персональных данных
    COOKIES = "cookies"  # Согласие на использование cookies
    MARKETING = "marketing"  # Согласие на маркетинговые коммуникации


class PrivacyConsent(IntIdPkMixin, Base):
    """Модель для хранения согласия на обработку персональных данных"""
    
    __table_args__ = (
        Index("idx_privacy_consent_user_id", "user_id"),
        Index("idx_privacy_consent_session_id", "session_id"),
        Index("idx_privacy_consent_type", "consent_type"),
    )
    
    # ID пользователя (если авторизован)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True
    )
    
    # ID сессии (для неавторизованных пользователей)
    session_id: Mapped[str | None] = mapped_column(nullable=True, index=True)
    
    # IP адрес пользователя
    ip_address: Mapped[str] = mapped_column(nullable=False)
    
    # User Agent браузера
    user_agent: Mapped[str] = mapped_column(nullable=False)
    
    # Тип согласия
    consent_type: Mapped[ConsentType] = mapped_column(nullable=False)
    
    # Статус согласия
    is_granted: Mapped[bool] = mapped_column(nullable=False, default=True)
    
    # Дата и время согласия
    granted_at: Mapped[datetime.datetime] = mapped_column(
        default=datetime.datetime.utcnow, nullable=False
    )
    
    # Текст политики конфиденциальности на момент согласия
    policy_version: Mapped[str] = mapped_column(nullable=False, default="1.0")
    
    # Связи
    user: Mapped["User"] = relationship(
        "User", back_populates="privacy_consents", lazy="joined"
    )
