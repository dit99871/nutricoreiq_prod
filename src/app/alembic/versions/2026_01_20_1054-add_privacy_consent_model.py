"""add_privacy_consent_model

Revision ID: 2026_01_20_1054
Revises: 2026_01_20_1054
Create Date: 2026-01-20 10:54:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "2025_01_20_1054"
down_revision: Union[str, None] = "0fe3bb26940a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Создаем enum тип для consent_type
    op.execute(
        "DO $$ BEGIN CREATE TYPE consenttype AS ENUM ('personal_data', 'cookies', 'marketing'); EXCEPTION WHEN duplicate_object THEN null; END $$"
    )

    # Создаем таблицу privacy_consents
    op.create_table(
        "privacy_consents",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("session_id", sa.String(), nullable=True),
        sa.Column("ip_address", sa.String(), nullable=False),
        sa.Column("user_agent", sa.String(), nullable=False),
        sa.Column(
            "consent_type",
            sa.Enum("personal_data", "cookies", "marketing", name="consenttype"),
            nullable=False,
        ),
        sa.Column("is_granted", sa.Boolean(), nullable=False),
        sa.Column("granted_at", sa.DateTime(), nullable=False),
        sa.Column("policy_version", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # Создаем индексы
    op.create_index("idx_privacy_consent_user_id", "privacy_consents", ["user_id"])
    op.create_index(
        "idx_privacy_consent_session_id", "privacy_consents", ["session_id"]
    )
    op.create_index("idx_privacy_consent_type", "privacy_consents", ["consent_type"])


def downgrade() -> None:
    # Удаляем индексы
    op.drop_index("idx_privacy_consent_type", table_name="privacy_consents")
    op.drop_index("idx_privacy_consent_session_id", table_name="privacy_consents")
    op.drop_index("idx_privacy_consent_user_id", table_name="privacy_consents")

    # Удаляем таблицу
    op.drop_table("privacy_consents")

    # Удаляем enum тип
    op.execute("DROP TYPE IF EXISTS consenttype")
