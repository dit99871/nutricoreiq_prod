"""
Тесты для product router.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import Request

from src.app.core.schemas.product import PendingProductCreate, UnifiedProductResponse


@pytest.fixture
def mock_request():
    """Создает мок для Request."""
    request = MagicMock(spec=Request)
    request.state = MagicMock()
    request.state.csp_nonce = "test_nonce"
    request.cookies = {}
    return request


@pytest.fixture
def mock_db_session():
    """Создает мок для DB session."""
    session = AsyncMock()
    return session


@pytest.fixture
def current_user():
    """Мок текущего пользователя."""
    user = MagicMock()
    user.id = 1
    user.username = "testuser"
    user.email = "test@example.com"
    return user


@pytest.fixture
def product_data():
    """Мок данных продукта."""
    return {
        "id": 1,
        "name": "Test Product",
        "calories": 100,
        "proteins": 10,
        "fats": 5,
        "carbs": 15,
    }


# --- search_products ---


@pytest.mark.asyncio
@patch("src.app.routers.product.handle_product_search")
async def test_search_products_success(
    mock_handle_product_search, mock_db_session
):
    """Тест успешного поиска продуктов."""
    from src.app.routers.product import search_products

    mock_response = UnifiedProductResponse(
        exact_match={
            "id": 1,
            "title": "Apple",
            "group_name": "Fruits",
            "proteins": {"total": 0.0},
            "fats": {"total": 0.0},
            "carbs": {"total": 0.0},
            "energy_value": 52.0,
            "water": 84.0,
        },
        suggestions=[],
    )
    mock_handle_product_search.return_value = mock_response

    result = await search_products(mock_db_session, "apple", confirmed=False)

    assert result == mock_response
    mock_handle_product_search.assert_called_once_with(
        mock_db_session, "apple", False
    )


@pytest.mark.asyncio
@patch("src.app.routers.product.handle_product_search")
async def test_search_products_confirmed(
    mock_handle_product_search, mock_db_session
):
    """Тест поиска продуктов с подтверждением."""
    from src.app.routers.product import search_products

    mock_response = UnifiedProductResponse(
        exact_match={
            "id": 1,
            "title": "Apple",
            "group_name": "Fruits",
            "proteins": {"total": 0.0},
            "fats": {"total": 0.0},
            "carbs": {"total": 0.0},
            "energy_value": 52.0,
            "water": 84.0,
        },
        suggestions=[],
    )
    mock_handle_product_search.return_value = mock_response

    result = await search_products(mock_db_session, "apple", confirmed=True)

    assert result == mock_response
    mock_handle_product_search.assert_called_once_with(
        mock_db_session, "apple", True
    )


# --- get_product_details ---


@pytest.mark.asyncio
@patch("src.app.routers.product.get_redis_session_from_request")
@patch("src.app.routers.product.handle_product_details")
@patch("src.app.routers.product.templates.TemplateResponse")
async def test_get_product_details_success(
    mock_template_response,
    mock_handle_product_details,
    mock_get_redis_session,
    mock_request,
    current_user,
    mock_db_session,
    product_data,
):
    """Тест успешного получения деталей продукта."""
    from src.app.routers.product import get_product_details

    mock_handle_product_details.return_value = product_data
    mock_redis_session = MagicMock()
    mock_redis_session.get.return_value = "csrf_token_123"
    mock_get_redis_session.return_value = mock_redis_session
    mock_template_response.return_value = MagicMock()

    result = await get_product_details(
        mock_request, 1, mock_db_session, current_user
    )

    mock_handle_product_details.assert_called_once_with(mock_db_session, 1)
    mock_template_response.assert_called_once()
    call_kwargs = mock_template_response.call_args[1]
    assert call_kwargs["name"] == "product_detail.html"
    assert call_kwargs["request"] == mock_request
    assert call_kwargs["context"]["product"] == product_data
    assert call_kwargs["context"]["user"] == current_user


@pytest.mark.asyncio
@patch("src.app.routers.product.get_redis_session_from_request")
@patch("src.app.routers.product.handle_product_details")
@patch("src.app.routers.product.templates.TemplateResponse")
async def test_get_product_details_no_user(
    mock_template_response,
    mock_handle_product_details,
    mock_get_redis_session,
    mock_request,
    mock_db_session,
    product_data,
):
    """Тест получения деталей продукта без авторизации."""
    from src.app.routers.product import get_product_details

    mock_handle_product_details.return_value = product_data
    mock_redis_session = MagicMock()
    mock_redis_session.get.return_value = "csrf_token_123"
    mock_get_redis_session.return_value = mock_redis_session
    mock_template_response.return_value = MagicMock()

    result = await get_product_details(mock_request, 1, mock_db_session, None)

    call_kwargs = mock_template_response.call_args[1]
    assert call_kwargs["context"]["user"] is None


# --- add_pending_product ---


@pytest.mark.asyncio
@patch("src.app.routers.product.create_pending_product")
async def test_add_pending_product_success(
    mock_create_pending_product, mock_db_session
):
    """Тест успешного добавления продукта в очередь ожидания."""
    from src.app.routers.product import add_pending_product

    data = PendingProductCreate(name="New Product")

    await add_pending_product(data, mock_db_session)

    mock_create_pending_product.assert_called_once_with(mock_db_session, "New Product")


@pytest.mark.asyncio
@patch("src.app.routers.product.create_pending_product")
async def test_add_pending_product_with_long_name(
    mock_create_pending_product, mock_db_session
):
    """Тест добавления продукта с длинным названием."""
    from src.app.routers.product import add_pending_product

    long_name = "Long Product Name"
    data = PendingProductCreate(name=long_name)

    await add_pending_product(data, mock_db_session)

    mock_create_pending_product.assert_called_once_with(mock_db_session, long_name)
