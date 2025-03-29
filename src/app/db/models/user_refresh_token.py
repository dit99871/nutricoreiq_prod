from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base
from .mixins.int_id_pk import IntIdPkMixin


class UserRefreshToken(IntIdPkMixin, Base):
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    hashed_refresh_token: Mapped[str]  # Храним в зашифрованном виде

    users: Mapped["User"] = relationship(back_populates="user_refresh_tokens")
