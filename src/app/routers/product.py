from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse, ORJSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.core import db_helper
from src.app.core.logger import get_logger
from src.app.repo.product import handle_product_search, handle_product_details
from src.app.core.services.redis import get_redis_session_from_request
from src.app.core.services.user_service import UserService
from src.app.core.utils import templates
from src.app.core.utils.pending_product import create_pending_product
from src.app.schemas.product import PendingProductCreate, UnifiedProductResponse
from src.app.schemas.user import UserPublic

log = get_logger("product_router")

router = APIRouter(
    tags=["Product"],
    default_response_class=ORJSONResponse,
)

session_dep = Annotated[AsyncSession, Depends(db_helper.session_getter)]


@router.get("/search", response_model=UnifiedProductResponse)
async def search_products(
    session: session_dep,
    query: str = Query(..., min_length=3),
    confirmed: bool = Query(False),
):
    """
    Searches for products based on a query string.

    This endpoint performs a search for products by matching the query string
    against the product titles in the database. It returns a `UnifiedProductResponse`
    containing an exact match if found, or suggests similar products.

    :param session: The current database session.
    :param query: The search query string. It must be at least 2 characters long.
    :param confirmed: A boolean flag indicating whether to skip suggestions.
    :return: A `UnifiedProductResponse` object with the search results.
    """

    return await handle_product_search(session, query, confirmed)


@router.get("/{product_id}", response_class=HTMLResponse)
@router.head("/{product_id}")
async def get_product_details(
    request: Request,
    product_id: int,
    session: session_dep,
    current_user: Annotated[UserPublic, Depends(UserService.get_user_by_access_jwt)],
):
    """
    Retrieves the details of a product.

    This endpoint retrieves the details of a product and renders its information
    using an HTML template.

    :param request: The incoming request object.
    :param product_id: The ID of the product to retrieve.
    :param session: The current database session.
    :param current_user: The authenticated user object obtained from the dependency.
    :return: A rendered HTML template with the product details.
    """

    product_data = await handle_product_details(session, product_id)
    # log.info("Rendering template")
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
    session: session_dep,
):
    """
    Adds a new pending product to the database.

    This endpoint checks if a product with the given name is already in the pending
    queue. If not, it adds the product to the queue.

    :param data: The pending product data containing the product name.
    :param session: The current database session.
    :raises HTTPException: If the product is already in the pending queue.
    :return: A JSON response indicating success.
    """

    await create_pending_product(session, data.name)
