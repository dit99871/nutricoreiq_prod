import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from unittest.mock import MagicMock, patch

from sqlalchemy.sql.expression import select

from app.db import db_helper
from app.db.models import Base
from src.app.main import app
from src.app.db.models.product import Product
from src.app.db.models.pending_product import PendingProduct
from src.app.schemas.user import UserResponse


from src.app.core.config import settings


# Фикстура для тестовой сессии с PostgreSQL
@pytest.fixture(scope="function")
async def async_session():
    test_url = settings.db.test_url or settings.db.url
    engine = create_async_engine(
        str(test_url),
        echo=settings.db.test_echo or settings.db.echo,
        pool_size=settings.db.pool_size,
        max_overflow=settings.db.max_overflow,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    TestingSessionLocal = sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )
    async with TestingSessionLocal() as session:
        yield session
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


# Фикстура для клиента FastAPI
@pytest.fixture(scope="function")
async def client(async_session):
    async def get_session_override():
        return async_session

    app.dependency_overrides[db_helper.session_getter] = get_session_override
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


# Мок для текущего пользователя
@pytest.fixture
def mock_current_user():
    return UserResponse(
        id=1, uid="user1", username="testuser", email="test@example.com"
    )


# Мок для шаблонов
@pytest.fixture
def mock_templates():
    return MagicMock()


# Тесты для эндпоинта /search
@pytest.mark.asyncio
async def test_search_products_exact_match(client, async_session):
    product = Product(
        id=1, title="Test Product", search_vector="test", product_groups_id=1
    )
    async_session.add(product)
    await async_session.commit()

    response = await client.get("/search?query=Test Product&confirmed=false")
    assert response.status_code == 200
    data = response.json()
    assert data["exact_match"] is not None
    assert data["exact_match"]["title"] == "Test Product"
    assert len(data["suggestions"]) == 0


@pytest.mark.asyncio
async def test_search_products_suggestions(client, async_session):
    product1 = Product(
        id=1, title="Test Product 1", search_vector="test", product_groups_id=1
    )
    product2 = Product(
        id=2, title="Test Product 2", search_vector="test", product_groups_id=1
    )
    async_session.add_all([product1, product2])
    await async_session.commit()

    response = await client.get("/search?query=test&confirmed=false")
    assert response.status_code == 200
    data = response.json()
    assert data["exact_match"] is None
    assert len(data["suggestions"]) > 0
    assert all(
        s["title"] in ["Test Product 1", "Test Product 2"] for s in data["suggestions"]
    )


@pytest.mark.asyncio
async def test_search_products_confirmed(client, async_session):
    with patch(
        "src.app.services.pending_product.create_pending_product"
    ) as mock_create:
        response = await client.get("/search?query=New Product&confirmed=true")
        assert response.status_code == 200
        data = response.json()
        assert data["pending_added"] is True
        assert data["exact_match"] is None
        assert len(data["suggestions"]) == 0
        mock_create.assert_called_once()


# Тесты для эндпоинта /{product_id}
@pytest.mark.asyncio
async def test_get_product_details_success(
    client, async_session, mock_current_user, mock_templates
):
    product = Product(id=1, title="Test Product", product_groups_id=1)
    async_session.add(product)
    await async_session.commit()

    with patch("src.app.utils.templates.templates", new=mock_templates):
        mock_templates.TemplateResponse.return_value = b"HTML content"
        response = await client.get("/1")
        assert response.status_code == 200
        assert b"HTML content" in response.content
        mock_templates.TemplateResponse.assert_called_once()


@pytest.mark.asyncio
async def test_get_product_details_not_found(
    client, async_session, mock_current_user, mock_templates
):
    with patch("src.app.utils.templates.templates", new=mock_templates):
        mock_templates.TemplateResponse.return_value = b"HTML content"
        response = await client.get("/999")
        assert response.status_code == 404
        assert response.json()["detail"] == "Продукт не найден"


# Тесты для эндпоинта /pending
@pytest.mark.asyncio
async def test_add_pending_product_success(client, async_session):
    data = {"name": "New Pending Product"}
    response = await client.post("/pending", json=data)
    assert response.status_code == 200
    assert response.json() == {"status": "success"}

    result = await async_session.execute(
        select(PendingProduct).where(PendingProduct.name == "New Pending Product")
    )
    assert result.scalar() is not None


@pytest.mark.asyncio
async def test_add_pending_product_duplicate(client, async_session):
    async_session.add(PendingProduct(name="Duplicate Product"))
    await async_session.commit()

    data = {"name": "Duplicate Product"}
    response = await client.post("/pending", json=data)
    assert response.status_code == 400
    assert response.json()["detail"] == "Продукт уже в очереди"
