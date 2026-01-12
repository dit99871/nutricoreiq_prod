import pytest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import HTTPException, status

from src.app.core.repo import handle_product_search, handle_product_details


class FakeResult:
    def __init__(self, scalar=None, scalars=None):
        self._scalar = scalar
        self._scalars = scalars or []

    def unique(self):
        return self

    def scalar_one_or_none(self):
        return self._scalar

    def scalars(self):
        class _ScalarResult:
            def __init__(self, data):
                self._data = data

            def all(self):
                return self._data

        return _ScalarResult(self._scalars)


@pytest.mark.asyncio
async def test_handle_product_search_exact_match():
    session = AsyncMock()
    product = MagicMock(id=1, title="Творог")
    session.execute.return_value = FakeResult(scalar=product)

    with (
        patch("src.app.repo.product.map_to_schema", return_value="mapped_product") as mock_mapper,
        patch("src.app.repo.product.create_pending_product", new_callable=AsyncMock) as mock_pending,
    ):
        response = await handle_product_search(session, " Творог ", confirmed=False)

    assert response.exact_match == "mapped_product"
    assert response.suggestions == []
    assert response.pending_added is False
    mock_mapper.assert_called_once_with(product)
    mock_pending.assert_not_awaited()
    session.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_product_search_returns_suggestions():
    session = AsyncMock()
    suggestion_products = [
        SimpleNamespace(
            id=idx,
            title=f"Продукт {idx}",
            product_groups=SimpleNamespace(name="Группа"),
        )
        for idx in range(1, 3)
    ]
    session.execute = AsyncMock(
        side_effect=[
            FakeResult(scalar=None),
            FakeResult(scalars=suggestion_products),
        ]
    )

    with patch("src.app.repo.product.create_pending_product", new_callable=AsyncMock) as mock_pending:
        response = await handle_product_search(session, "молоко", confirmed=False)

    assert response.exact_match is None
    assert len(response.suggestions) == 2
    assert response.suggestions[0].title == "Продукт 1"
    assert response.pending_added is False
    mock_pending.assert_not_called()
    assert session.execute.await_count == 2


@pytest.mark.asyncio
async def test_handle_product_search_confirmed_adds_pending():
    session = AsyncMock()
    session.execute.return_value = FakeResult(scalar=None)

    with patch("src.app.repo.product.create_pending_product", new_callable=AsyncMock) as mock_pending:
        mock_pending.return_value = True
        response = await handle_product_search(session, "  Киноа  ", confirmed=True)

    assert response.exact_match is None
    assert response.suggestions == []
    assert response.pending_added is True
    mock_pending.assert_awaited_once()
    args, kwargs = mock_pending.await_args
    assert args[0] is session
    assert args[1] == "киноа"
    assert kwargs == {"raise_if_exists": False}


@pytest.mark.asyncio
async def test_handle_product_search_confirmed_already_exists():
    session = AsyncMock()
    session.execute.return_value = FakeResult(scalar=None)

    with patch("src.app.repo.product.create_pending_product", new_callable=AsyncMock) as mock_pending:
        mock_pending.return_value = False
        response = await handle_product_search(session, "Какао", confirmed=True)

    assert response.exact_match is None
    assert response.suggestions == []
    assert response.pending_added is False
    mock_pending.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_product_details_success():
    session = AsyncMock()
    product = MagicMock(id=7)
    session.execute.return_value = FakeResult(scalar=product)

    with patch("src.app.repo.product.map_to_schema", return_value="product_details") as mock_mapper:
        response = await handle_product_details(session, product_id=7)

    assert response == "product_details"
    mock_mapper.assert_called_once_with(product)
    session.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_product_details_not_found():
    session = AsyncMock()
    session.execute.return_value = FakeResult(scalar=None)

    with pytest.raises(HTTPException) as exc_info:
        await handle_product_details(session, product_id=999)

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
    assert exc_info.value.detail["message"] == "Продукт не найден"
    session.execute.assert_awaited_once()
