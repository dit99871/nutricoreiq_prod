"""Update Nutrients&Products relationships

Revision ID: e503f1417e42
Revises: b8fffdf5021d
Create Date: 2025-03-28 09:16:03.016666

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "e503f1417e42"
down_revision: Union[str, None] = "b8fffdf5021d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("products", sa.Column("group_id", sa.Integer(), nullable=False))
    op.create_foreign_key(
        op.f("fk_products_group_id_product_groups"),
        "products",
        "product_groups",
        ["group_id"],
        ["id"],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(
        op.f("fk_products_group_id_product_groups"),
        "products",
        type_="foreignkey",
    )
    op.drop_column("products", "group_id")
