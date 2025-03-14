"""create DeletedUser model

Revision ID: acaf7eaf0569
Revises: 6c635e67e1e3
Create Date: 2025-03-14 17:48:00.846674

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "acaf7eaf0569"
down_revision: Union[str, None] = "6c635e67e1e3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "deleted_users",
        sa.PrimaryKeyConstraint("id", name=op.f("pk_deleted_users")),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("username", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("hashed_password", sa.String(), nullable=False),
        sa.Column("gender", sa.String(), nullable=False),
        sa.Column("age", sa.Integer(), nullable=False),
        sa.Column("weight", sa.Float(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("is_admin", sa.Boolean(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=False),
)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("deleted_users")
