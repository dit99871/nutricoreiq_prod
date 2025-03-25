"""Create Products & Nutrients

Revision ID: 2fc116aa23af
Revises: d18298e4e283
Create Date: 2025-03-25 12:59:15.510906

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "2fc116aa23af"
down_revision: Union[str, None] = "d18298e4e283"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "nutrients",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_nutrients")),
        sa.Column("name", sa.String(), nullable=False),
        sa.UniqueConstraint("name", name=op.f("uq_nutrients_name")),
    )
    op.create_table(
        "product_groups",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_product_groups")),
        sa.Column("name", sa.String(), nullable=False),
    )
    op.create_table(
        "products",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_products")),
        sa.Column("title", sa.String(), nullable=False),

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
    op.drop_table("product_groups")
    op.drop_table("nutrients")
