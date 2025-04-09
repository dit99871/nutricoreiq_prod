"""Update models for product query

Revision ID: aa3978ee3f98
Revises: 60d81f8c9e2d
Create Date: 2025-04-09 09:45:23.979464

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "aa3978ee3f98"
down_revision: Union[str, None] = "60d81f8c9e2d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column(
        "product_nutrients",
        "amount",
        existing_type=sa.DOUBLE_PRECISION(precision=53),
        nullable=True,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column(
        "product_nutrients",
        "amount",
        existing_type=sa.DOUBLE_PRECISION(precision=53),
        nullable=False,
    )
