"""Create PendingProduct + update User

Revision ID: 722564dd4ef4
Revises: b98dc783677e
Create Date: 2025-04-11 11:09:50.040679

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "722564dd4ef4"
down_revision: Union[str, None] = "b98dc783677e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "pending_products",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=40), nullable=False),
        sa.Column("created_at", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_pending_products")),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("pending_products")
