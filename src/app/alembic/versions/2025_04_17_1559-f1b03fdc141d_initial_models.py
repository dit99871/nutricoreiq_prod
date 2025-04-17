"""Initial models

Revision ID: f1b03fdc141d
Revises:
Create Date: 2025-04-17 15:59:08.103342

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "f1b03fdc141d"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "nutrients",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("unit", sa.String(), nullable=False),
        sa.Column(
            "category",
            sa.Enum(
                "MACRO",
                "ENERGY_VALUE",
                "NONESSENTIAL_AMINO",
                "ESSENTIAL_AMINO",
                "COND_ESSENTIAL_AMINO",
                "SATURATED_FATS",
                "MONOUNSATURATED_FATS",
                "POLYUNSATURATED_FATS",
                "FATS",
                "CARBS",
                "VITAMINS",
                "VITAMIN_LIKE",
                "MINERALS_MACRO",
                "MINERALS_MICRO",
                "OTHER",
                name="nutrientcategory",
            ),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_nutrients")),
        sa.UniqueConstraint("name", name=op.f("uq_nutrients_name")),
    )
    op.create_table(
        "pending_products",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=40), nullable=False),
        sa.Column("created_at", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_pending_products")),
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
        sa.Column(
            "gender",
            sa.Enum("female", "male", native_enum=False),
            nullable=True,
        ),
        sa.Column("age", sa.Integer(), nullable=True),
        sa.Column("weight", sa.Float(), nullable=True),
        sa.Column("height", sa.Float(), nullable=True),
        sa.Column(
            "kfa",
            sa.Enum("1", "2", "3", "4", "5", native_enum=False),
            nullable=True,
        ),
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
        sa.Column("amount", sa.Float(), nullable=True),
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
    op.drop_table("pending_products")
    op.drop_table("nutrients")
