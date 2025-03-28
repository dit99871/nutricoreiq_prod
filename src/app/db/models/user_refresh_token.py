import datetime as dt
from datetime import datetime

from sqlalchemy import ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base
from .mixins.int_id_pk import IntIdPkMixin


class UserRefreshToken(IntIdPkMixin, Base):
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    hashed_refresh_token: Mapped[bytes]  # Храним в зашифрованном виде
    expires_at: Mapped[str] = mapped_column(index=True)
    created_at: Mapped[str] = mapped_column(
        default=datetime.now(dt.UTC).isoformat(),
    )

    user: Mapped["User"] = relationship(back_populates="user_refresh_tokens")
