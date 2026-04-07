"""Переименование меток ENUM (userrole, goaltype, kfalevel) под ORM имена

Revision ID: e1a2b3c4d5f6
Revises: d68eba96118e
Create Date: 2025-08-21 09:50:00

"""

from typing import Sequence, Union

from alembic import op

revision: str = "e1a2b3c4d5f6"
down_revision: Union[str, None] = "d68eba96118e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # userrole: 'user','admin','moderator' -> 'USER','ADMIN','MODERATOR'
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
               SELECT 1 FROM pg_type t JOIN pg_enum e ON e.enumtypid=t.oid
               WHERE t.typname='userrole' AND e.enumlabel='user'
            ) THEN
               ALTER TYPE userrole RENAME VALUE 'user' TO 'USER';
            END IF;

            IF EXISTS (
               SELECT 1 FROM pg_type t JOIN pg_enum e ON e.enumtypid=t.oid
               WHERE t.typname='userrole' AND e.enumlabel='admin'
            ) THEN
               ALTER TYPE userrole RENAME VALUE 'admin' TO 'ADMIN';
            END IF;

            IF EXISTS (
               SELECT 1 FROM pg_type t JOIN pg_enum e ON e.enumtypid=t.oid
               WHERE t.typname='userrole' AND e.enumlabel='moderator'
            ) THEN
               ALTER TYPE userrole RENAME VALUE 'moderator' TO 'MODERATOR';
            END IF;
        END $$;
        """)

    # goaltype: русские строки -> имена Enum
    # 'Снижение веса' -> 'LOSE_WEIGHT', 'Увеличение веса' -> 'GAIN_WEIGHT', 'Поддержание веса' -> 'MAINTAIN_WEIGHT'
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
               SELECT 1 FROM pg_type t JOIN pg_enum e ON e.enumtypid=t.oid
               WHERE t.typname='goaltype' AND e.enumlabel='Снижение веса'
            ) THEN
               ALTER TYPE goaltype RENAME VALUE 'Снижение веса' TO 'LOSE_WEIGHT';
            END IF;

            IF EXISTS (
               SELECT 1 FROM pg_type t JOIN pg_enum e ON e.enumtypid=t.oid
               WHERE t.typname='goaltype' AND e.enumlabel='Увеличение веса'
            ) THEN
               ALTER TYPE goaltype RENAME VALUE 'Увеличение веса' TO 'GAIN_WEIGHT';
            END IF;

            IF EXISTS (
               SELECT 1 FROM pg_type t JOIN pg_enum e ON e.enumtypid=t.oid
               WHERE t.typname='goaltype' AND e.enumlabel='Поддержание веса'
            ) THEN
               ALTER TYPE goaltype RENAME VALUE 'Поддержание веса' TO 'MAINTAIN_WEIGHT';
            END IF;
        END $$;
        """)

    # kfalevel: '1'..'5' -> 'VERY_LOW','LOW','MEDIUM','HIGH','VERY_HIGH'
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
               SELECT 1 FROM pg_type t JOIN pg_enum e ON e.enumtypid=t.oid
               WHERE t.typname='kfalevel' AND e.enumlabel='1'
            ) THEN
               ALTER TYPE kfalevel RENAME VALUE '1' TO 'VERY_LOW';
            END IF;

            IF EXISTS (
               SELECT 1 FROM pg_type t JOIN pg_enum e ON e.enumtypid=t.oid
               WHERE t.typname='kfalevel' AND e.enumlabel='2'
            ) THEN
               ALTER TYPE kfalevel RENAME VALUE '2' TO 'LOW';
            END IF;

            IF EXISTS (
               SELECT 1 FROM pg_type t JOIN pg_enum e ON e.enumtypid=t.oid
               WHERE t.typname='kfalevel' AND e.enumlabel='3'
            ) THEN
               ALTER TYPE kfalevel RENAME VALUE '3' TO 'MEDIUM';
            END IF;

            IF EXISTS (
               SELECT 1 FROM pg_type t JOIN pg_enum e ON e.enumtypid=t.oid
               WHERE t.typname='kfalevel' AND e.enumlabel='4'
            ) THEN
               ALTER TYPE kfalevel RENAME VALUE '4' TO 'HIGH';
            END IF;

            IF EXISTS (
               SELECT 1 FROM pg_type t JOIN pg_enum e ON e.enumtypid=t.oid
               WHERE t.typname='kfalevel' AND e.enumlabel='5'
            ) THEN
               ALTER TYPE kfalevel RENAME VALUE '5' TO 'VERY_HIGH';
            END IF;
        END $$;
        """)


def downgrade() -> None:
    # Обратные переименования (имена Enum -> исходные значения)
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
               SELECT 1 FROM pg_type t JOIN pg_enum e ON e.enumtypid=t.oid
               WHERE t.typname='userrole' AND e.enumlabel='USER'
            ) THEN
               ALTER TYPE userrole RENAME VALUE 'USER' TO 'user';
            END IF;

            IF EXISTS (
               SELECT 1 FROM pg_type t JOIN pg_enum e ON e.enumtypid=t.oid
               WHERE t.typname='userrole' AND e.enumlabel='ADMIN'
            ) THEN
               ALTER TYPE userrole RENAME VALUE 'ADMIN' TO 'admin';
            END IF;

            IF EXISTS (
               SELECT 1 FROM pg_type t JOIN pg_enum e ON e.enumtypid=t.oid
               WHERE t.typname='userrole' AND e.enumlabel='MODERATOR'
            ) THEN
               ALTER TYPE userrole RENAME VALUE 'MODERATOR' TO 'moderator';
            END IF;
        END $$;
        """)

    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
               SELECT 1 FROM pg_type t JOIN pg_enum e ON e.enumtypid=t.oid
               WHERE t.typname='goaltype' AND e.enumlabel='LOSE_WEIGHT'
            ) THEN
               ALTER TYPE goaltype RENAME VALUE 'LOSE_WEIGHT' TO 'Снижение веса';
            END IF;

            IF EXISTS (
               SELECT 1 FROM pg_type t JOIN pg_enum e ON e.enumtypid=t.oid
               WHERE t.typname='goaltype' AND e.enumlabel='GAIN_WEIGHT'
            ) THEN
               ALTER TYPE goaltype RENAME VALUE 'GAIN_WEIGHT' TO 'Увеличение веса';
            END IF;

            IF EXISTS (
               SELECT 1 FROM pg_type t JOIN pg_enum e ON e.enumtypid=t.oid
               WHERE t.typname='goaltype' AND e.enumlabel='MAINTAIN_WEIGHT'
            ) THEN
               ALTER TYPE goaltype RENAME VALUE 'MAINTAIN_WEIGHT' TO 'Поддержание веса';
            END IF;
        END $$;
        """)

    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
               SELECT 1 FROM pg_type t JOIN pg_enum e ON e.enumtypid=t.oid
               WHERE t.typname='kfalevel' AND e.enumlabel='VERY_LOW'
            ) THEN
               ALTER TYPE kfalevel RENAME VALUE 'VERY_LOW' TO '1';
            END IF;

            IF EXISTS (
               SELECT 1 FROM pg_type t JOIN pg_enum e ON e.enumtypid=t.oid
               WHERE t.typname='kfalevel' AND e.enumlabel='LOW'
            ) THEN
               ALTER TYPE kfalevel RENAME VALUE 'LOW' TO '2';
            END IF;

            IF EXISTS (
               SELECT 1 FROM pg_type t JOIN pg_enum e ON e.enumtypid=t.oid
               WHERE t.typname='kfalevel' AND e.enumlabel='MEDIUM'
            ) THEN
               ALTER TYPE kfalevel RENAME VALUE 'MEDIUM' TO '3';
            END IF;

            IF EXISTS (
               SELECT 1 FROM pg_type t JOIN pg_enum e ON e.enumtypid=t.oid
               WHERE t.typname='kfalevel' AND e.enumlabel='HIGH'
            ) THEN
               ALTER TYPE kfalevel RENAME VALUE 'HIGH' TO '4';
            END IF;

            IF EXISTS (
               SELECT 1 FROM pg_type t JOIN pg_enum e ON e.enumtypid=t.oid
               WHERE t.typname='kfalevel' AND e.enumlabel='VERY_HIGH'
            ) THEN
               ALTER TYPE kfalevel RENAME VALUE 'VERY_HIGH' TO '5';
            END IF;
        END $$;
        """)
