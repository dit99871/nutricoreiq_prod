"""Update models for products

Revision ID: 6c2a586143b9
Revises: 60d81f8c9e2d
Create Date: 2025-04-09 09:13:31.964875

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "6c2a586143b9"
down_revision: Union[str, None] = "60d81f8c9e2d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
