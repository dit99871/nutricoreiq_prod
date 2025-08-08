# from datetime import datetime


# class DeletedUser(IntIdPkMixin, Base):
#     username: Mapped[str]
#     email: Mapped[str]
#     hashed_password: Mapped[bytes]
#     gender: Mapped[str]
#     age: Mapped[int]
#     weight: Mapped[float]
#
#     is_active: Mapped[bool]
#     deleted_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
