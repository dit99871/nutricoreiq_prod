"""Add search vector, triggers and funcs to products

Revision ID: d709ad587862
Revises: 8e881b9feeec
Create Date: 2025-04-26 19:33:09.823171

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "d709ad587862"
down_revision: Union[str, None] = "8e881b9feeec"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Устанавливаем необходимое расширение
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")

    op.add_column(
        "products",
        sa.Column("search_vector", postgresql.TSVECTOR(), nullable=True),
    )

    # Сначала создаем функцию и триггер
    op.execute(
        """
        CREATE OR REPLACE FUNCTION update_product_search_vector() 
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.search_vector = 
                setweight(to_tsvector('russian', coalesce(NEW.title, '')), 'A');
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )

    op.execute(
        """
        CREATE TRIGGER product_search_vector_update
        BEFORE INSERT OR UPDATE ON products
        FOR EACH ROW EXECUTE FUNCTION update_product_search_vector();
        """
    )

    # Затем создаем индексы
    op.create_index(
        "idx_product_search_vector",
        "products",
        ["search_vector"],
        unique=False,
        postgresql_using="gin",
    )

    op.create_index(
        "idx_product_title_trgm",
        "products",
        ["title"],
        unique=False,
        postgresql_using="gin",
        postgresql_ops={"title": "gin_trgm_ops"},
    )

    # Обновляем записи
    op.execute(
        """
        UPDATE products 
        SET search_vector = NULL;
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("idx_product_title_trgm", table_name="products")
    op.drop_index("idx_product_search_vector", table_name="products")
    op.drop_column("products", "search_vector")
    op.execute("DROP TRIGGER IF EXISTS product_search_vector_update ON products;")
    op.execute("DROP FUNCTION IF EXISTS update_product_search_vector;")
    # Не удаляем расширение, так как оно может использоваться другими таблицами
