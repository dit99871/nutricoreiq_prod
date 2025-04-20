"""Update ProductNutrient model by default value to amount

Revision ID: 395b5b88de34
Revises: f1b03fdc141d
Create Date: 2025-04-20 09:32:58.758038

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "395b5b88de34"
down_revision: Union[str, None] = "f1b03fdc141d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column(
        "product_nutrients",
        "amount",
        existing_type=sa.DOUBLE_PRECISION(precision=53),
        nullable=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column(
        "product_nutrients",
        "amount",
        existing_type=sa.DOUBLE_PRECISION(precision=53),
        nullable=True,
    )
