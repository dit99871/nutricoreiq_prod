"""Update format data in User model

Revision ID: 03637b8bb72b
Revises: 395b5b88de34
Create Date: 2025-04-24 09:29:27.573028

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "03637b8bb72b"
down_revision: Union[str, None] = "395b5b88de34"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
