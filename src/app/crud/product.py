from typing import Sequence

from fastapi import HTTPException
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from core.logger import get_logger
from db.models import Product, ProductNutrient

log = get_logger("crud_product")


async def search_products(self, query: str, limit: int = 5):
    """
        Searches for products by a given query.

        Constructs a SQLAlchemy query to search for products matching the given
        query string. The query will look for products whose title contains the
        query string, or whose search vector contains the query string.

        :param query: The query string to search for.
        :param limit: The maximum number of products to return. Defaults to 5.
        :return: A list of products matching the query.
        """
    result = await self.session.execute(
        select(Product).where(
            or_(
                func.lower(Product.title) == func.lower(query),
                Product.search_vector.op("@@")(
                    func.websearch_to_tsquery("russian", query)
                ),
            ).limit(limit)
        )
    )
    return result.scalars().all()


async def get_product_with_nutrients(self, product_id: int):
    """
    Fetches a product by ID from the database with its nutrient associations.

    Constructs a SQLAlchemy query to fetch a product by its ID, and also fetches
    its associated nutrients.

    :param product_id: The ID of the product to fetch.
    :return: The fetched product.
    """
    result = await self.session.execute(
        select(Product)
        .options(
            joinedload(Product.nutrient_associations).joinedload(
                ProductNutrient.nutrients
            )
        )
        .where(Product.id == product_id)
    )
    return result.scalar()


async def get_exact_product(session: AsyncSession, query: str) -> Product | None:
    result = await session.execute(select(Product).where(Product.title.ilike(query)))
    return result.scalar()


async def get_suggested_products(
    session: AsyncSession, query: str, limit: int = 5
) -> Sequence[Product]:
    """
    Fetches a list of products from the database based on a search query.

    Given a `query` argument and an optional `limit` argument, constructs a SQLAlchemy
    query to fetch a list of products from the database. The query will look for
    products whose title contains the query string.

    :param session: The current database session.
    :param query: The search query to look for.
    :param limit: The maximum number of products to return. Defaults to 5.
    :return: A list of products matching the query.
    """
    result = await session.execute(
        select(Product).where(Product.title.ilike(f"%{query}%")).limit(limit)
    )
    return result.scalars().all()
