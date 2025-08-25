"""Remove id from product_nutrients and add CASCADE on delete

Revision ID: 0fe3bb26940a
Revises: a7b3e2c9d1f4
Create Date: 2025-08-25 10:52:28.573676

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0fe3bb26940a"
down_revision: Union[str, None] = "a7b3e2c9d1f4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Check if id column exists before trying to drop it
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col["name"] for col in inspector.get_columns("product_nutrients")]

    # Drop foreign key constraints
    op.drop_constraint(
        "fk_product_nutrients_nutrient_id_nutrients",
        "product_nutrients",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_product_nutrients_product_id_products",
        "product_nutrients",
        type_="foreignkey",
    )

    # Only drop id column if it exists
    if "id" in columns:
        op.drop_column("product_nutrients", "id")

    # Recreate foreign keys with CASCADE
    op.create_foreign_key(
        "fk_product_nutrients_product_id_products",
        "product_nutrients",
        "products",
        ["product_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_product_nutrients_nutrient_id_nutrients",
        "product_nutrients",
        "nutrients",
        ["nutrient_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Drop foreign keys first
    op.drop_constraint(
        "fk_product_nutrients_nutrient_id_nutrients",
        "product_nutrients",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_product_nutrients_product_id_products",
        "product_nutrients",
        type_="foreignkey",
    )

    # Add id column if it doesn't exist
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col["name"] for col in inspector.get_columns("product_nutrients")]

    if "id" not in columns:
        op.add_column(
            "product_nutrients",
            sa.Column("id", sa.INTEGER(), autoincrement=True, nullable=False),
        )

    # Recreate foreign keys without CASCADE
    op.create_foreign_key(
        "fk_product_nutrients_product_id_products",
        "product_nutrients",
        "products",
        ["product_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_product_nutrients_nutrient_id_nutrients",
        "product_nutrients",
        "nutrients",
        ["nutrient_id"],
        ["id"],
    )
