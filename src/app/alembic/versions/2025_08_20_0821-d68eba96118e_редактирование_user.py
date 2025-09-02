"""Редактирование User

Revision ID: d68eba96118e
Revises: c1354cf1145d
Create Date: 2025-08-20 08:21:32.214937

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "d68eba96118e"
down_revision: Union[str, None] = "c1354cf1145d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create enum types first
    kfalevel_enum = postgresql.ENUM("1", "2", "3", "4", "5", name="kfalevel")
    kfalevel_enum.create(op.get_bind())

    goaltype_enum = postgresql.ENUM(
        "Снижение веса", "Увеличение веса", "Поддержание веса", name="goaltype"
    )
    goaltype_enum.create(op.get_bind())

    userrole_enum = postgresql.ENUM("user", "admin", "moderator", name="userrole")
    userrole_enum.create(op.get_bind())

    # Now alter the columns to use the new enum types
    # For the role column
    op.alter_column(
        "users",
        "role",
        type_=userrole_enum,
        postgresql_using="lower(role)::userrole",
        existing_type=sa.VARCHAR(),
        existing_nullable=False,
    )

    # For the goal column (handle spaces and case)
    op.alter_column(
        "users",
        "goal",
        type_=goaltype_enum,
        postgresql_using="goal::goaltype",
        existing_type=sa.VARCHAR(length=16),
        existing_nullable=True,
    )

    # For the kfa column
    op.alter_column(
        "users",
        "kfa",
        type_=kfalevel_enum,
        postgresql_using="kfa::kfalevel",
        existing_type=sa.VARCHAR(length=1),
        existing_nullable=True,
    )

    # Alter created_at and add indexes
    op.alter_column(
        "users",
        "created_at",
        type_=sa.DateTime(),
        existing_type=sa.VARCHAR(),
        existing_nullable=False,
        postgresql_using=(
            "CASE "
            "WHEN created_at ~ '^[0-9]{2}[.][0-9]{2}[.][0-9]{4} [0-9]{2}:[0-9]{2}:[0-9]{2}$' "
            "THEN to_timestamp(created_at, 'DD.MM.YYYY HH24:MI:SS')::timestamp "
            "ELSE created_at::timestamp "
            "END"
        ),
    )

    op.create_index(op.f("ix_users_created_at"), "users", ["created_at"], unique=False)
    op.create_index(op.f("ix_users_is_active"), "users", ["is_active"], unique=False)
    op.create_index(op.f("ix_users_uid"), "users", ["uid"], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_users_uid"), table_name="users")
    op.drop_index(op.f("ix_users_is_active"), table_name="users")
    op.drop_index(op.f("ix_users_created_at"), table_name="users")

    op.alter_column(
        "users",
        "created_at",
        type_=sa.VARCHAR(),
        existing_type=sa.DateTime(),
        existing_nullable=False,
    )

    op.alter_column(
        "users",
        "role",
        type_=sa.VARCHAR(),
        postgresql_using="role::text",
        existing_nullable=False,
    )

    op.alter_column(
        "users",
        "goal",
        type_=sa.Text(),
        postgresql_using="goal::text",
        existing_nullable=True,
    )

    op.alter_column(
        "users",
        "kfa",
        type_=sa.Text(),
        postgresql_using="kfa::text",
        existing_nullable=True,
    )

    # Drop the enum types
    op.execute("DROP TYPE IF EXISTS userrole CASCADE")
    op.execute("DROP TYPE IF EXISTS goaltype CASCADE")
    op.execute("DROP TYPE IF EXISTS kfalevel CASCADE")
