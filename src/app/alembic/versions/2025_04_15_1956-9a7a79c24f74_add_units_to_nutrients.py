"""Add units to nutrients

Revision ID: 9a7a79c24f74
Revises: f02101570248
Create Date: 2025-04-15 19:56:57.133775

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "9a7a79c24f74"
down_revision: Union[str, None] = "f02101570248"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("nutrients", sa.Column("unit", sa.String(), nullable=False))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("nutrients", "unit")
