import pytest
from unittest.mock import AsyncMock, Mock, patch
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.services.product import handle_product_search, handle_product_details
from src.app.db.models import Product, PendingProduct, ProductNutrient
from src.app.schemas.product import (
    UnifiedProductResponse,
    ProductDetailResponse,
    ProductSuggestion,
)


# Фикстура для создания тестовой сессии
@pytest.fixture
def mock_session():
    return AsyncMock(spec=AsyncSession)


# Фикстура для создания тестового продукта
@pytest.fixture
def mock_product():
    product = Mock(spec=Product)
    product.id = 1
    product.title = "test product"
    product.product_groups = Mock()
    product.product_groups.name = "Test Group"
    product.nutrient_associations = []
    return product


# Тесты для handle_product_search
@pytest.mark.asyncio
async def test_handle_product_search_exact_match(mock_session, mock_product):
    """Проверяет поиск с точным совпадением."""
    result = Mock()
    result.unique.return_value.scalar_one_or_none.return_value = mock_product
    mock_session.execute.return_value = result
    with patch(
        "src.app.services.product.map_to_schema",
        return_value=ProductDetailResponse(
            id=1, title="test product", group_name="Test Group"
        ),
    ) as mock_map:
        response = await handle_product_search(mock_session, "test product", False)
    assert response.exact_match == ProductDetailResponse(
        id=1, title="test product", group_name="Test Group"
    )
    assert response.suggestions == []
    assert response.pending_added is False
    mock_map.assert_called_once_with(mock_product)
    mock_session.execute.assert_called()


@pytest.mark.asyncio
async def test_handle_product_search_suggestions(mock_session, mock_product):
    """Проверяет поиск с предложениями."""
    result_exact = Mock()
    result_exact.unique.return_value.scalar_one_or_none.return_value = None
    result_suggestions = Mock()
    result_suggestions.unique.return_value.scalars.return_value.all.return_value = [
        mock_product
    ]
    mock_session.execute.side_effect = [result_exact, result_suggestions]
    response = await handle_product_search(mock_session, "test", False)
    assert len(response.suggestions) == 1
    assert response.suggestions[0] == ProductSuggestion(
        id=1, title="test product", group_name="Test Group"
    )
    assert response.exact_match is None
    assert response.pending_added is False
    mock_session.execute.assert_called()


@pytest.mark.asyncio
async def test_handle_product_search_pending_added(mock_session):
    """Проверяет добавление в очередь pending при confirmed=True."""
    result_exact = Mock()
    result_exact.unique.return_value.scalar_one_or_none.return_value = None
    result_pending = Mock()
    result_pending.scalar.return_value = None
    mock_session.execute.side_effect = [result_exact, result_pending]
    with patch(
        "src.app.db.models.PendingProduct",
        return_value=Mock(spec=PendingProduct, name="new product"),
    ):
        response = await handle_product_search(mock_session, "new product", True)
    assert response.pending_added is True
    assert response.exact_match is None
    assert response.suggestions == []
    mock_session.add.assert_called_once()
    mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_handle_product_search_error(mock_session):
    """Проверяет обработку ошибки базы данных."""
    mock_session.execute.side_effect = Exception("Database error")
    with pytest.raises(HTTPException) as exc:
        await handle_product_search(mock_session, "test", False)
    assert exc.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert exc.value.detail == "Database error"
    mock_session.rollback.assert_called_once()


# Тесты для handle_product_details
@pytest.mark.asyncio
async def test_handle_product_details_success(mock_session, mock_product):
    """Проверяет успешное получение деталей продукта."""
    result = Mock()
    result.unique.return_value.scalar_one_or_none.return_value = mock_product
    mock_session.execute.return_value = result
    with patch(
        "src.app.services.product.map_to_schema",
        return_value=ProductDetailResponse(
            id=1, title="test product", group_name="Test Group"
        ),
    ) as mock_map:
        response = await handle_product_details(mock_session, 1)
    assert response == ProductDetailResponse(
        id=1, title="test product", group_name="Test Group"
    )
    mock_map.assert_called_once_with(mock_product)
    mock_session.execute.assert_called()


@pytest.mark.asyncio
async def test_handle_product_details_not_found(mock_session):
    """Проверяет обработку случая, когда продукт не найден."""
    result = Mock()
    result.unique.return_value.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = result
    with pytest.raises(HTTPException) as exc:
        await handle_product_details(mock_session, 1)
    assert exc.value.status_code == status.HTTP_404_NOT_FOUND
    assert exc.value.detail == "Продукт не найден"


@pytest.mark.asyncio
async def test_handle_product_details_error(mock_session):
    """Проверяет обработку ошибки базы данных."""
    mock_session.execute.side_effect = Exception("Database error")
    with pytest.raises(HTTPException) as exc:
        await handle_product_details(mock_session, 1)
    assert exc.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert exc.value.detail == "Database error"
