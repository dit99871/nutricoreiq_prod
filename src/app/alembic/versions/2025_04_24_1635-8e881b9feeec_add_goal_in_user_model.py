"""Add goal in User model

Revision ID: 8e881b9feeec
Revises: 03637b8bb72b
Create Date: 2025-04-24 16:35:04.906999

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "8e881b9feeec"
down_revision: Union[str, None] = "03637b8bb72b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "users",
        sa.Column(
            "goal",
            sa.Enum(
                "Снижение веса",
                "Увеличение веса",
                "Поддержание веса",
                native_enum=False,
            ),
            nullable=True,
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("users", "goal")
