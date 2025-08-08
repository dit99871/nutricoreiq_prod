from fastapi import HTTPException, status
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from src.app.core.logger import get_logger
from src.app.models import Product, PendingProduct, ProductNutrient
from src.app.schemas.product import (
    ProductDetailResponse,
    ProductSuggestion,
    UnifiedProductResponse,
)
from src.app.utils.product import map_to_schema

log = get_logger("product_services")


async def handle_product_search(
    session: AsyncSession,
    query: str,
    confirmed: bool,
) -> UnifiedProductResponse:
    """
    Searches for products based on a query string.

    This function performs a search for products by matching the query string
    against the product titles in the database. It returns a `UnifiedProductResponse`
    containing an exact match if found, or suggests similar products.

    The function takes a query string and a boolean flag indicating whether to skip
    suggestions.

    If the `confirmed` flag is set to `True`, the function adds the product to the
    pending queue if it does not already exist.

    If a database error occurs, raises an `HTTPException` with a 404 status code and
    a detail string containing the error message. If an unexpected error occurs,
    raises an `HTTPException` with a 500 status code and a detail string containing the
    error message.

    :param session: The current database session.
    :param query: The search query string. It must be at least 2 characters long.
    :param confirmed: A boolean flag indicating whether to skip suggestions.
    :return: A `UnifiedProductResponse` object with the search results.
    """
    response = UnifiedProductResponse()
    query = query.strip().lower()

    exact_match = await session.execute(
        select(Product)
        .options(
            selectinload(Product.product_groups),
            selectinload(Product.nutrient_associations).selectinload(
                ProductNutrient.nutrients
            ),
        )
        .where(func.lower(Product.title) == query)
    )
    product = exact_match.unique().scalar_one_or_none()

    if product:
        # log.info("Точное совпадение: %s", product.title)
        response.exact_match = map_to_schema(product)
        return response

    # Поиск предложений
    if not confirmed:
        # log.info("Поиск предложений: %s", query)
        suggestions = await session.execute(
            select(Product)
            .options(
                selectinload(Product.product_groups),
                selectinload(Product.nutrient_associations).selectinload(
                    ProductNutrient.nutrients
                ),
            )
            .where(
                or_(
                    Product.search_vector.op("@@")(
                        func.websearch_to_tsquery("russian", query)
                    ),
                    Product.title.ilike(f"%{query}%"),
                )
            )
            .order_by(
                func.ts_rank(
                    Product.search_vector,
                    func.websearch_to_tsquery("russian", query),
                )
            )
            .limit(5)
        )
        suggestions = suggestions.unique().scalars().all()

        if suggestions:
            # log.info("Загрузка предложений: %s", query)
            response.suggestions = [
                ProductSuggestion(
                    id=p.id, title=p.title, group_name=p.product_groups.name
                )
                for p in suggestions
            ]
            return response

    if confirmed:
        exists = await session.execute(
            select(PendingProduct).where(func.lower(PendingProduct.name) == query)
        )
        if not exists.scalar():
            # log.info("Добавление в очередь: %s", query)
            new_pending = PendingProduct(name=query)
            session.add(new_pending)
            await session.commit()
            response.pending_added = True

    return response


async def handle_product_details(
    session: AsyncSession,
    product_id: int,
) -> ProductDetailResponse:
    """
    Retrieves the details of a product by its ID.

    This function queries the database for a product with the given `product_id`.
    It uses eager loading to fetch related product groups and nutrient associations
    for efficient data retrieval. If the product is found, it is mapped to a
    `ProductDetailResponse` schema and returned. If the product is not found, an
    HTTP 404 exception is raised. In case of other exceptions, an HTTP 500 exception
    is raised with the error details.

    :param session: The current database session.
    :param product_id: The unique identifier of the product to retrieve.
    :return: A `ProductDetailResponse` object containing the product details.
    """
    # log.info("Start product detail handler")
    product = await session.execute(
        select(Product)
        .options(
            joinedload(Product.product_groups),
            joinedload(Product.nutrient_associations).joinedload(
                ProductNutrient.nutrients
            ),
        )
        .where(Product.id == product_id)
    )
    product = product.unique().scalar_one_or_none()

    if not product:
        log.error(
            "Продукт с id %s не найден",
            product_id,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "message": "Продукт не найден",
                "details": f"Product with id {product_id} not found",
            },
        )

    return map_to_schema(product)
