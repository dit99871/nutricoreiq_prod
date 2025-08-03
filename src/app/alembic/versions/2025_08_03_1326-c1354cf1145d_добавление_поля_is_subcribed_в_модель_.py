"""Добавление поля is_subcribed в модель User

Revision ID: c1354cf1145d
Revises: 12d9ec7a4890
Create Date: 2025-08-03 13:26:29.446455

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c1354cf1145d"
down_revision: Union[str, None] = "12d9ec7a4890"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "users",
        sa.Column(
            "is_subscribed", sa.Boolean(), nullable=False, server_default="FALSE"
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("users", "is_subscribed")
