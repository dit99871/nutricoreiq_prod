from datetime import datetime

from fastapi import APIRouter, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse

from src.app.core.dependencies import db_session_dep, current_user_dep
from src.app.core.logger import get_logger
from src.app.core.repo.product import handle_product_search, handle_product_details
from src.app.core.repo.pending_product import create_pending_product
from src.app.core.services.redis import get_redis_session_from_request
from src.app.core.utils import templates
from src.app.core.schemas.product import PendingProductCreate, UnifiedProductResponse

log = get_logger("product_router")

router = APIRouter(
    tags=["Product"],
    default_response_class=JSONResponse,
)


@router.get("/search", response_model=UnifiedProductResponse)
async def search_products(
    session: db_session_dep,
    query: str = Query(..., min_length=3),
    confirmed: bool = Query(False),
):
    """
    Ищет продукты на основе строки запроса.

    Этот эндпоинт выполняет поиск продуктов путем сопоставления строки запроса
    с названиями продуктов в базе данных. Возвращает `UnifiedProductResponse`
    содержащий точное совпадение, если найдено, или предлагает похожие продукты.

    :param session: Текущая сессия базы данных.
    :param query: Строка поискового запроса. Должна содержать минимум 3 символа.
    :param confirmed: Булев флаг, указывающий нужно ли пропускать предложения.
    :return: Объект `UnifiedProductResponse` с результатами поиска.
    """

    return await handle_product_search(session, query, confirmed)


@router.get("/{product_id}", response_class=HTMLResponse)
@router.head("/{product_id}")
async def get_product_details(
    request: Request,
    product_id: int,
    session: db_session_dep,
    current_user: current_user_dep,
):
    """
    Получает детали продукта.

    Этот эндпоинт получает детали продукта и отображает его информацию
    с использованием HTML-шаблона.

    :param request: Входящий объект запроса.
    :param product_id: ID продукта для получения.
    :param session: Текущая сессия базы данных.
    :param current_user: Аутентифицированный объект пользователя, полученный из зависимости.
    :return: Отрендеренный HTML-шаблон с деталями продукта.
    """

    product_data = await handle_product_details(session, product_id)
    log.debug("Rendering template")
    redis_session = get_redis_session_from_request(request)

    return templates.TemplateResponse(
        request=request,
        name="product_detail.html",
        context={
            "current_year": datetime.now().year,
            "product": product_data,
            "user": current_user,
            "csrf_token": redis_session.get("csrf_token"),
            "csp_nonce": request.state.csp_nonce,
        },
    )


@router.post("/pending")
async def add_pending_product(
    data: PendingProductCreate,
    session: db_session_dep,
):
    """
    Добавляет новый ожидающий продукт в базу данных.

    Этот эндпоинт проверяет, находится ли продукт с заданным именем уже в очереди
    ожидания. Если нет, добавляет продукт в очередь.

    :param data: Данные ожидающего продукта, содержащие название продукта.
    :param session: Текущая сессия базы данных.
    :raises HTTPException: Если продукт уже находится в очереди ожидания.
    :return: JSON-ответ, указывающий на успех.
    """

    await create_pending_product(session, data.name)
