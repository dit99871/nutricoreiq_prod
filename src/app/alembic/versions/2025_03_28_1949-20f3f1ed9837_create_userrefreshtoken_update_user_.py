"""Create UserRefreshToken + update User model

Revision ID: 20f3f1ed9837
Revises: e503f1417e42
Create Date: 2025-03-28 19:49:22.031058

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20f3f1ed9837"
down_revision: Union[str, None] = "e503f1417e42"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "user_refresh_tokens",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("hashed_refresh_token", sa.LargeBinary(), nullable=False),
        sa.Column("expires_at", sa.String(), nullable=False),
        sa.Column("created_at", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_user_refresh_tokens_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_user_refresh_tokens")),
    )
    op.create_index(
        op.f("ix_user_refresh_tokens_expires_at"),
        "user_refresh_tokens",
        ["expires_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_user_refresh_tokens_user_id"),
        "user_refresh_tokens",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        op.f("ix_user_refresh_tokens_user_id"),
        table_name="user_refresh_tokens",
    )
    op.drop_index(
        op.f("ix_user_refresh_tokens_expires_at"),
        table_name="user_refresh_tokens",
    )
    op.drop_table("user_refresh_tokens")
