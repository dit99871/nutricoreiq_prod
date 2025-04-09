"""Update Nutrient model

Revision ID: b98dc783677e
Revises: aa3978ee3f98
Create Date: 2025-04-09 13:36:15.607143

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from db.models.nutrient import NutrientCategory


revision: str = "b98dc783677e"
down_revision: Union[str, None] = "aa3978ee3f98"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        "CREATE TYPE nutrientcategory AS ENUM ('macro', 'energy_value', 'nonessentional_amino', 'essential_amino', 'cond_essential_amino', 'saturated_fats', 'monounsaturated_fats', 'polyunsaturated_fats', 'fats', 'carbs', 'vitamins', 'vitamin_like', 'minerals_macro', 'minerals_micro', 'other')"
    )
    op.add_column(
        "nutrients",
        sa.Column(
            "category",
            sa.Enum(NutrientCategory, name="nutrientcategory", native_enum=True),
            nullable=False,
            default=NutrientCategory.OTHER,
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("nutrients", "category")
