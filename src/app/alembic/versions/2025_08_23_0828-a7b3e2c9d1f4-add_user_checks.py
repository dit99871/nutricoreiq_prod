"""Добавление CHECK-ограничений для users.age/height/weight

Revision ID: a7b3e2c9d1f4
Revises: d68eba96118e
Create Date: 2025-08-23 08:28:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "a7b3e2c9d1f4"
down_revision: Union[str, None] = "d68eba96118e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Добавляем CHECK-ограничения на таблицу users
    op.create_check_constraint(
        constraint_name="ck_users_age_range",
        table_name="users",
        condition=sa.text("age IS NULL OR (age >= 10 AND age <= 120)"),
    )
    op.create_check_constraint(
        constraint_name="ck_users_height_range",
        table_name="users",
        condition=sa.text("height IS NULL OR (height >= 50 AND height <= 300)"),
    )
    op.create_check_constraint(
        constraint_name="ck_users_weight_range",
        table_name="users",
        condition=sa.text("weight IS NULL OR (weight >= 20 AND weight <= 400)"),
    )


def downgrade() -> None:
    # Удаляем CHECK-ограничения
    op.drop_constraint("ck_users_weight_range", table_name="users", type_="check")
    op.drop_constraint("ck_users_height_range", table_name="users", type_="check")
    op.drop_constraint("ck_users_age_range", table_name="users", type_="check")
