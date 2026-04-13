"""ORM-миксины для моделей."""

from sqlalchemy.orm import Mapped, mapped_column


class IntIdPkMixin:
    """Миксин с целочисленным первичным ключом `id`."""

    id: Mapped[int] = mapped_column(primary_key=True)
