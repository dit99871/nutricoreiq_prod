import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.app.core.exceptions import ValidationError, ConflictError
from src.app.core.repo.pending_product import (
    create_pending_product,
    pending_product_exists,
)


class FakeExecuteResult:
    def __init__(self, scalar):
        self._scalar = scalar

    def scalar_one_or_none(self):
        return self._scalar


@pytest.mark.asyncio
async def test_pending_product_exists_found():
    session = AsyncMock()
    session.execute.return_value = FakeExecuteResult(scalar=object())

    result = await pending_product_exists(session, "  Какао  ")

    assert result is True
    session.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_pending_product_exists_not_found():
    session = AsyncMock()
    session.execute.return_value = FakeExecuteResult(scalar=None)

    result = await pending_product_exists(session, "миндаль")

    assert result is False
    session.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_pending_product_exists_empty_name():
    session = AsyncMock()

    result = await pending_product_exists(session, "   ")

    assert result is False
    session.execute.assert_not_called()


@pytest.mark.asyncio
async def test_create_pending_product_success():
    session = AsyncMock()
    session.add = MagicMock()

    with patch(
        "src.app.core.repo.pending_product.pending_product_exists",
        new_callable=AsyncMock,
    ) as mock_exists, patch(
        "src.app.core.repo.pending_product.PendingProduct"
    ) as mock_model:
        mock_exists.return_value = False
        new_pending_instance = MagicMock()
        mock_model.return_value = new_pending_instance

        created = await create_pending_product(session, "  Киноа  ")

    assert created is True
    mock_exists.assert_awaited_once_with(session, "Киноа")
    mock_model.assert_called_once_with(name="Киноа")
    session.add.assert_called_once_with(new_pending_instance)
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_pending_product_empty_name():
    session = AsyncMock()

    with pytest.raises(ValidationError) as exc_info:
        await create_pending_product(session, "   ")

    assert exc_info.value.message == "Название продукта не может быть пустым"
    session.execute.assert_not_called()
    session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_create_pending_product_exists_raise():
    session = AsyncMock()

    with patch(
        "src.app.core.repo.pending_product.pending_product_exists",
        new_callable=AsyncMock,
    ) as mock_exists:
        mock_exists.return_value = True

        with pytest.raises(ConflictError) as exc_info:
            await create_pending_product(session, "Орехи")

    assert exc_info.value.message == "Продукт уже в очереди на добавление"
    mock_exists.assert_awaited_once_with(session, "Орехи")
    session.add.assert_not_called()
    session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_create_pending_product_exists_no_raise():
    session = AsyncMock()

    with patch(
        "src.app.core.repo.pending_product.pending_product_exists",
        new_callable=AsyncMock,
    ) as mock_exists:
        mock_exists.return_value = True

        created = await create_pending_product(
            session,
            "овсянка",
            raise_if_exists=False,
        )

    assert created is False
    mock_exists.assert_awaited_once_with(session, "овсянка")
    session.add.assert_not_called()
    session.commit.assert_not_awaited()
