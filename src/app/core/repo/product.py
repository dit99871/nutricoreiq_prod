from src.app.core.exceptions import NotFoundError
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload

from src.app.core.logger import get_logger
from src.app.core.models import Product, ProductNutrient
from src.app.core.services.product_service import ProductService
from src.app.core.schemas.product import (
    ProductDetailResponse,
    ProductSuggestion,
    UnifiedProductResponse,
)
from src.app.core.repo.pending_product import create_pending_product

log = get_logger("product_repo")


async def handle_product_search(
    session: AsyncSession,
    query: str,
    confirmed: bool,
) -> UnifiedProductResponse:
    """
    Ищет продукты на основе строки запроса.

    Эта функция выполняет поиск продуктов путем сопоставления строки запроса
    с названиями продуктов в базе данных. Она возвращает `UnifiedProductResponse`,
    содержащий точное совпадение, если найдено, или предлагает похожие продукты.

    Функция принимает строку запроса и булев флаг, указывающий, нужно ли
    пропускать предложения.

    Если флаг `confirmed` установлен в `True`, функция добавляет продукт в
    очередь ожидания, если он еще не существует.

    При ошибке базы данных вызывает `HTTPException` с кодом 404 и
    сообщением об ошибке. При неожиданной ошибке вызывает `HTTPException`
    с кодом 500 и сообщением об ошибке.

    :param session: Текущая сессия базы данных.
    :param query: Строка поискового запроса. Должна содержать минимум 2 символа.
    :param confirmed: Булев флаг, указывающий, нужно ли пропускать предложения.
    :return: Объект `UnifiedProductResponse` с результатами поиска.
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
        log.debug("Точное совпадение: %s", product.title)
        response.exact_match = ProductService.map_to_schema(product)
        return response

    # поиск предложений
    if not confirmed:
        log.debug("Поиск предложений: %s", query)
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
            log.debug("Загрузка предложений: %s", query)
            response.suggestions = [
                ProductSuggestion(
                    id=p.id, title=p.title, group_name=p.product_groups.name
                )
                for p in suggestions
            ]
            return response

    if confirmed:
        created = await create_pending_product(
            session,
            query,
            raise_if_exists=False,
        )
        if created:
            response.pending_added = True

    return response


async def handle_product_details(
    session: AsyncSession,
    product_id: int,
) -> ProductDetailResponse:
    """
    Получает детали продукта по его ID.

    Эта функция запрашивает в базе данных продукт с указанным `product_id`.
    Она использует загрузку связанных данных для получения связанных групп продуктов
    и ассоциаций нутриентов для эффективного извлечения данных. Если продукт найден,
    он преобразуется в схему `ProductDetailResponse` и возвращается. Если продукт
    не найден, вызывается исключение HTTP 404. В случае других исключений вызывается
    исключение HTTP 500 с деталями ошибки.

    :param session: Текущая сессия базы данных.
    :param product_id: Уникальный идентификатор продукта для получения.
    :return: Объект `ProductDetailResponse`, содержащий детали продукта.
    :raises NotFoundError: Если продукт не найден
    """

    log.debug("Start product detail handler")
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
        raise NotFoundError("Продукт не найден", resource_type="product")

    return ProductService.map_to_schema(product)
