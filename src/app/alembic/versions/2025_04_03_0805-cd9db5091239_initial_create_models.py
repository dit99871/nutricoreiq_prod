"""Initial create models

Revision ID: cd9db5091239
Revises:
Create Date: 2025-04-03 08:05:41.680066

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "cd9db5091239"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "nutrients",
        sa.PrimaryKeyConstraint("id", name=op.f("pk_nutrients")),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.UniqueConstraint("name", name=op.f("uq_nutrients_name")),
    )
    op.create_table(
        "product_groups",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_product_groups")),
    )
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("uid", sa.String(), nullable=False),
        sa.Column("username", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("hashed_password", sa.LargeBinary(), nullable=False),
        sa.Column("gender", sa.String(), nullable=True),
        sa.Column("age", sa.Integer(), nullable=True),
        sa.Column("weight", sa.Float(), nullable=True),
        sa.Column("height", sa.Float(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("created_at", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)
    op.create_index(op.f("ix_users_username"), "users", ["username"], unique=True)
    op.create_table(
        "products",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("group_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["group_id"],
            ["product_groups.id"],
            name=op.f("fk_products_group_id_product_groups"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_products")),
    )
    op.create_table(
        "product_nutrients",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("nutrient_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["nutrient_id"],
            ["nutrients.id"],
            name=op.f("fk_product_nutrients_nutrient_id_nutrients"),
        ),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
            name=op.f("fk_product_nutrients_product_id_products"),
        ),
        sa.PrimaryKeyConstraint(
            "product_id",
            "nutrient_id",
            "id",
            name=op.f("pk_product_nutrients"),
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("product_nutrients")
    op.drop_table("products")
    op.drop_index(op.f("ix_users_username"), table_name="users")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")
    op.drop_table("product_groups")
    op.drop_table("nutrients")
