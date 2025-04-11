"""Update User model by kfa

Revision ID: f02101570248
Revises: 722564dd4ef4
Create Date: 2025-04-11 12:57:05.606712

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f02101570248"
down_revision: Union[str, None] = "722564dd4ef4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "users",
        sa.Column(
            "kfa",
            sa.Enum("1", "2", "3", "4", "5", native_enum=False),
            nullable=True,
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("users", "kfa")
