from typing import Annotated

from fastapi import APIRouter, Depends, Request, Query, HTTPException, status
from fastapi.responses import ORJSONResponse, HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from services.pending_product import check_pending_exists, create_pending_product
from db import db_helper
from schemas.product import UnifiedProductResponse, PendingProductCreate
from services.product import handle_product_search, handle_product_details
from utils.security import generate_csp_nonce
from utils.templates import templates

router = APIRouter(
    tags=["Product"],
    default_response_class=ORJSONResponse,
)


# routers/products.py
@router.get("/search", response_model=UnifiedProductResponse)
async def search_products(
    session: Annotated[AsyncSession, Depends(db_helper.session_getter)],
    query: str = Query(..., min_length=2),
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
async def get_product_details(
    request: Request,
    product_id: int,
    session: Annotated[AsyncSession, Depends(db_helper.session_getter)],
):
    """
    Retrieves the details of a product.

    This endpoint retrieves the details of a product and renders its information
    using a HTML template.

    :param request: The incoming request object.
    :param product_id: The ID of the product to retrieve.
    :param session: The current database session.
    :return: A rendered HTML template with the product details.
    """
    product_data = await handle_product_details(session, product_id)
    return templates.TemplateResponse(
        request=request,
        name="product_detail.html",
        context={
            "product": product_data,
            "csp_nonce": generate_csp_nonce(),
        },
    )


@router.post("/pending")
async def add_pending_product(
    data: PendingProductCreate,
    session: Annotated[AsyncSession, Depends(db_helper.session_getter)],
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
    if await check_pending_exists(session, data.name):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Продукт уже в очереди",
        )

    await create_pending_product(session, data.name)
    return {"status": "success"}
