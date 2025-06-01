import pytest
from unittest.mock import AsyncMock, Mock, patch
from sqlalchemy.ext.asyncio import AsyncSession
from src.app.services.pending_product import (
    check_pending_exists,
    create_pending_product,
)
from src.app.db.models import PendingProduct


# Фикстура для создания тестовой сессии
@pytest.fixture
def mock_session():
    return AsyncMock(spec=AsyncSession)


# Тесты для check_pending_exists
@pytest.mark.asyncio
async def test_check_pending_exists_exists(mock_session):
    """Проверяет, что функция возвращает True, если продукт существует."""
    result = Mock()
    result.scalar.return_value = Mock(spec=PendingProduct, id=1, name="Test Product")
    mock_session.execute.return_value = result
    exists = await check_pending_exists(mock_session, "Test Product")
    assert exists is True
    mock_session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_check_pending_exists_not_exists(mock_session):
    """Проверяет, что функция возвращает False, если продукт не существует."""
    result = Mock()
    result.scalar.return_value = None
    mock_session.execute.return_value = result
    exists = await check_pending_exists(mock_session, "Nonexistent Product")
    assert exists is False
    mock_session.execute.assert_called_once()


# Тесты для create_pending_product
@pytest.mark.asyncio
async def test_create_pending_product_success(mock_session):
    """Проверяет успешное создание нового pending продукта."""
    name = "Test Product"
    with patch(
        "src.app.db.models.PendingProduct",
        return_value=Mock(spec=PendingProduct, id=1, name=name),
    ):
        await create_pending_product(mock_session, name)
    mock_session.add.assert_called_once()
    mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_create_pending_product_error(mock_session):
    """Проверяет обработку ошибки при commit."""
    name = "Test Product"
    with patch(
        "src.app.db.models.PendingProduct",
        return_value=Mock(spec=PendingProduct, id=1, name=name),
    ):
        mock_session.commit.side_effect = Exception("Database error")
        with pytest.raises(Exception) as exc:
            await create_pending_product(mock_session, name)
        assert str(exc.value) == "Database error"
    mock_session.add.assert_called_once()
    mock_session.commit.assert_called_once()
