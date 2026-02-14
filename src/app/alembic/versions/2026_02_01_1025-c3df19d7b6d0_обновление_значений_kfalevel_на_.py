"""Обновление значений KFALevel на коэффициенты активности

Revision ID: c3df19d7b6d0
Revises: 2025_01_20_1054
Create Date: 2026-02-01 10:25:43.817325

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c3df19d7b6d0"
down_revision: Union[str, None] = "2025_01_20_1054"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Обновляем enum тип consent_type на верхний регистр
    op.execute("ALTER TYPE consenttype RENAME TO consenttype_old")
    op.execute("CREATE TYPE consenttype AS ENUM ('PERSONAL_DATA', 'COOKIES', 'MARKETING')")
    op.execute("ALTER TABLE privacy_consents ALTER COLUMN consent_type TYPE consenttype USING consent_type::text::consenttype")
    op.execute("DROP TYPE consenttype_old")


def downgrade() -> None:
    """Downgrade schema."""
    # Возвращаем enum тип в нижний регистр
    op.execute("ALTER TYPE consenttype RENAME TO consenttype_upper")
    op.execute("CREATE TYPE consenttype AS ENUM ('personal_data', 'cookies', 'marketing')")
    op.execute("ALTER TABLE privacy_consents ALTER COLUMN consent_type TYPE consenttype USING consent_type::text::consenttype")
    op.execute("DROP TYPE consenttype_upper")
