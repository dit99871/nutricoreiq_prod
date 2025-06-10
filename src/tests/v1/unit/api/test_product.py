import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi import HTTPException, status

from src.app.api.v1.product import (
    search_products,
    get_product_details,
    add_pending_product,
)
from src.app.schemas.product import (
    UnifiedProductResponse,
    PendingProductCreate,
    ProductSuggestion,
    ProductDetailResponse,
)
from src.app.schemas.user import UserResponse
from src.app.services.product import handle_product_search, handle_product_details
from src.app.services.pending_product import (
    check_pending_exists,
    create_pending_product,
)
from src.app.utils.templates import templates


# Фикстура для мок-сеанса
@pytest.fixture
def mock_session():
    return MagicMock()


# Фикстура для мок-пользователя
@pytest.fixture
def mock_current_user():
    return UserResponse(
        id=1, uid="user1", username="testuser", email="test@example.com"
    )


# Фикстура для мок-запроса
@pytest.fixture
def mock_request():
    return MagicMock()


# Фикстура для мок-шаблона
@pytest.fixture
def mock_templates():
    mock_template = MagicMock()
    mock_template.TemplateResponse.return_value = "Mocked HTML"
    with patch("src.app.api.v1.product.templates", new=mock_template):
        yield mock_template


# Фикстура для мок-генерации CSP nonce
@pytest.fixture
def mock_generate_csp_nonce():
    with patch(
        "src.app.api.v1.product.generate_csp_nonce", return_value="mocked_nonce"
    ) as mock_nonce:
        yield mock_nonce


# Тесты для эндпоинта /search
@pytest.mark.asyncio
async def test_search_products_exact_match(mock_session):
    mock_exact_match = ProductDetailResponse(
        id=1, title="Test Product", group_name="Test Group"
    )
    mock_response = UnifiedProductResponse(exact_match=mock_exact_match)
    with patch(
        "src.app.api.v1.product.handle_product_search", return_value=mock_response
    ) as mock_handle:
        result = await search_products(
            session=mock_session, query="Test Product", confirmed=False
        )
        assert result == mock_response
        mock_handle.assert_called_once_with(mock_session, "Test Product", False)


@pytest.mark.asyncio
async def test_search_products_suggestions(mock_session):
    mock_suggestion1 = ProductSuggestion(
        id=1, title="Test Product 1", group_name="Test Group"
    )
    mock_suggestion2 = ProductSuggestion(
        id=2, title="Test Product 2", group_name="Test Group"
    )
    mock_response = UnifiedProductResponse(
        suggestions=[mock_suggestion1, mock_suggestion2]
    )
    with patch(
        "src.app.api.v1.product.handle_product_search", return_value=mock_response
    ) as mock_handle:
        result = await search_products(
            session=mock_session, query="test", confirmed=False
        )
        assert result == mock_response
        mock_handle.assert_called_once_with(mock_session, "test", False)


@pytest.mark.asyncio
async def test_search_products_confirmed(mock_session):
    mock_response = UnifiedProductResponse(pending_added=True)
    with patch(
        "src.app.api.v1.product.handle_product_search", return_value=mock_response
    ) as mock_handle:
        result = await search_products(
            session=mock_session, query="New Product", confirmed=True
        )
        assert result == mock_response
        mock_handle.assert_called_once_with(mock_session, "New Product", True)


# Тесты для эндпоинта /{product_id}
@pytest.mark.asyncio
async def test_get_product_details_success(
    mock_session,
    mock_current_user,
    mock_request,
    mock_templates,
    mock_generate_csp_nonce,
):
    mock_product_data = ProductDetailResponse(
        id=1, title="Test Product", group_name="Test Group"
    )
    with patch(
        "src.app.api.v1.product.handle_product_details", return_value=mock_product_data
    ) as mock_handle:
        result = await get_product_details(
            request=mock_request,
            product_id=1,
            session=mock_session,
            current_user=mock_current_user,
        )
        assert result == "Mocked HTML"
        mock_handle.assert_called_once_with(mock_session, 1)
        mock_templates.TemplateResponse.assert_called_once_with(
            request=mock_request,
            name="product_detail.html",
            context={
                "current_year": 2025,  # Текущий год (10 июня 2025)
                "product": mock_product_data,
                "user": mock_current_user,
                "csp_nonce": "mocked_nonce",  # Используем значение из мока
            },
        )


@pytest.mark.asyncio
async def test_get_product_details_not_found(
    mock_session,
    mock_current_user,
    mock_request,
    mock_templates,
    mock_generate_csp_nonce,
):
    with patch(
        "src.app.api.v1.product.handle_product_details",
        side_effect=HTTPException(status_code=404, detail="Продукт не найден"),
    ) as mock_handle:
        with pytest.raises(HTTPException) as exc:
            await get_product_details(
                request=mock_request,
                product_id=999,
                session=mock_session,
                current_user=mock_current_user,
            )
        assert exc.value.status_code == 404
        assert exc.value.detail == "Продукт не найден"
        mock_handle.assert_called_once_with(mock_session, 999)


# Тесты для эндпоинта /pending
@pytest.mark.asyncio
async def test_add_pending_product_success(mock_session):
    data = PendingProductCreate(name="New Pending Product")
    with patch(
        "src.app.api.v1.product.check_pending_exists", return_value=False
    ) as mock_check, patch(
        "src.app.api.v1.product.create_pending_product"
    ) as mock_create:
        result = await add_pending_product(data=data, session=mock_session)
        assert result == {"status": "success"}
        mock_check.assert_called_once_with(mock_session, "New Pending Product")
        mock_create.assert_called_once_with(mock_session, "New Pending Product")


@pytest.mark.asyncio
async def test_add_pending_product_duplicate(mock_session):
    data = PendingProductCreate(name="Duplicate Product")
    with patch(
        "src.app.api.v1.product.check_pending_exists", return_value=True
    ) as mock_check:
        with pytest.raises(HTTPException) as exc:
            await add_pending_product(data=data, session=mock_session)
        assert exc.value.status_code == 400
        assert exc.value.detail == "Продукт уже в очереди"
        mock_check.assert_called_once_with(mock_session, "Duplicate Product")
