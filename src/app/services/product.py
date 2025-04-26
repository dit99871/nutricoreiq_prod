from fastapi import HTTPException, status
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from db.models import Product, PendingProduct, ProductNutrient
from schemas.product import (
    ProductDetailResponse,
    ProductSuggestion,
    UnifiedProductResponse,
)
from utils.product import map_to_schema


async def handle_product_search(
    session: AsyncSession,
    query: str,
    confirmed: bool,
) -> UnifiedProductResponse:
    response = UnifiedProductResponse()
    query = query.strip().lower()

    try:
        # Точное совпадение с явной загрузкой
        exact_match = await session.execute(
            select(Product)
            .options(joinedload(Product.product_groups))
            .where(func.lower(Product.title) == query)
        )
        product = exact_match.unique().scalar_one_or_none()

        if product:
            response.exact_match = map_to_schema(product)
            return response

        # Поиск предложений
        if not confirmed:
            suggestions = await session.execute(
                select(Product)
                .options(
                    joinedload(Product.product_groups),
                    joinedload(Product.nutrient_associations),
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
                response.suggestions = [
                    ProductSuggestion(
                        id=p.id, title=p.title, group_name=p.product_groups.name
                    )
                    for p in suggestions
                ]
                return response

        # Обработка подтверждения
        if confirmed:
            exists = await session.execute(
                select(PendingProduct).where(func.lower(PendingProduct.name) == query)
            )
            if not exists.scalar():
                new_pending = PendingProduct(name=query)
                session.add(new_pending)
                await session.commit()
                response.pending_added = True

    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    return response


async def handle_product_details(
    session: AsyncSession, product_id: int
) -> ProductDetailResponse:
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
    product = product.scalar()

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Продукт не найден",
        )

    return map_to_schema(product)
