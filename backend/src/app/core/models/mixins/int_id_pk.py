from sqlalchemy.orm import mapped_column, Mapped


class IntIdPkMixin:
    id: Mapped[int] = mapped_column(primary_key=True)
