"""Update UserRefreshToken

Revision ID: 56a0dc87cb2a
Revises: 20f3f1ed9837
Create Date: 2025-03-29 14:49:43.848550

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "56a0dc87cb2a"
down_revision: Union[str, None] = "20f3f1ed9837"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column(
        "user_refresh_tokens",
        "hashed_refresh_token",
        existing_type=postgresql.BYTEA(),
        type_=sa.String(),
        existing_nullable=False,
    )
    op.drop_index("ix_user_refresh_tokens_expires_at", table_name="user_refresh_tokens")
    op.drop_column("user_refresh_tokens", "created_at")
    op.drop_column("user_refresh_tokens", "expires_at")


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column(
        "user_refresh_tokens",
        sa.Column("expires_at", sa.VARCHAR(), autoincrement=False, nullable=False),
    )
    op.add_column(
        "user_refresh_tokens",
        sa.Column("created_at", sa.VARCHAR(), autoincrement=False, nullable=False),
    )
    op.create_index(
        "ix_user_refresh_tokens_expires_at",
        "user_refresh_tokens",
        ["expires_at"],
        unique=False,
    )
    op.alter_column(
        "user_refresh_tokens",
        "hashed_refresh_token",
        existing_type=sa.String(),
        type_=postgresql.BYTEA(),
        existing_nullable=False,
    )
