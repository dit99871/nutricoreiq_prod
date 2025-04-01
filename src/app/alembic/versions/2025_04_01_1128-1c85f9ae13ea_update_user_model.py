"""Update User model

Revision ID: 1c85f9ae13ea
Revises: 56a0dc87cb2a
Create Date: 2025-04-01 11:28:35.238329

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "1c85f9ae13ea"
down_revision: Union[str, None] = "56a0dc87cb2a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("users", sa.Column("uid", sa.String(), nullable=False))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("users", "uid")
