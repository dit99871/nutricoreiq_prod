"""Update User model

Revision ID: b8fffdf5021d
Revises: 2fc116aa23af
Create Date: 2025-03-27 19:21:40.149300

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b8fffdf5021d"
down_revision: Union[str, None] = "2fc116aa23af"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column("users", "gender", existing_type=sa.VARCHAR(), nullable=True)
    op.alter_column("users", "age", existing_type=sa.INTEGER(), nullable=True)
    op.alter_column(
        "users",
        "weight",
        existing_type=sa.DOUBLE_PRECISION(precision=53),
        nullable=True,
    )
    op.alter_column("users", "height", existing_type=sa.INTEGER(), nullable=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column("users", "height", existing_type=sa.INTEGER(), nullable=False)
    op.alter_column(
        "users",
        "weight",
        existing_type=sa.DOUBLE_PRECISION(precision=53),
        nullable=False,
    )
    op.alter_column("users", "age", existing_type=sa.INTEGER(), nullable=False)
    op.alter_column("users", "gender", existing_type=sa.VARCHAR(), nullable=False)
