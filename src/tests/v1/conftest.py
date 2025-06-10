import os
import sys
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import text
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock

from src.app.core.config import settings
from src.app.core.redis import get_redis
from src.app.db import db_helper
from src.app.db.models import Base
from src.app.main import app

# Динамически добавляем src в sys.path
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src"))
if src_path not in sys.path:
    sys.path.insert(0, src_path)

# Определяем URL и echo для тестов
TEST_DATABASE_URL = str(settings.db.test_url or settings.db.url)  # Преобразуем в строку
SQLALCHEMY_ECHO = (
    settings.db.test_echo if settings.db.test_echo is not None else settings.db.echo
)

# Настраиваем pytest-asyncio для использования event_loop с областью session
pytest_asyncio.plugin.asyncio_default_loop_scope = "session"


# Фикстура для сброса состояния settings
@pytest.fixture(autouse=True, scope="function")
def reset_settings():
    """Сбрасывает settings.redis.salt до исходного значения перед и после каждого теста."""
    original_salt = settings.redis.salt
    yield
    settings.redis.salt = original_salt


@pytest.fixture(autouse=True, scope="session")
def setup_test_environment():
    """Настраиваем окружение для тестов."""
    os.environ["ENV"] = "test"
    os.environ["TESTING"] = "true"
    yield
    os.environ.pop("ENV", None)
    os.environ.pop("TESTING", None)


# Фикстура для интеграционных тестов
@pytest_asyncio.fixture(scope="session")
async def engine():
    """Создаем асинхронный движок для PostgreSQL и тестовую базу данных."""
    from sqlalchemy import NullPool

    # Подключаемся к серверу PostgreSQL (к базе 'postgres') для создания тестовой БД
    default_db_url = TEST_DATABASE_URL.replace("test_nutricoreiq", "postgres")
    temp_engine = create_async_engine(
        default_db_url,
        echo=SQLALCHEMY_ECHO,
        poolclass=NullPool,
    )

    # Проверяем и создаем тестовую базу данных, если она не существует
    async with temp_engine.connect() as conn:
        await conn.execute(text("COMMIT"))
        result = await conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = 'test_nutricoreiq'")
        )
        if result.scalar() is None:
            await conn.execute(text("CREATE DATABASE test_nutricoreiq"))
            await conn.execute(text("COMMIT"))
        await temp_engine.dispose()

    # Создаем движок для тестовой базы данных
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=SQLALCHEMY_ECHO,
        poolclass=NullPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)  # Очищаем таблицы перед созданием
        await conn.run_sync(Base.metadata.create_all)  # Создаем все таблицы
    yield engine
    # Очистка после завершения тестов
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(engine):
    """Создаем асинхронную сессию для тестов с транзакцией и откатом."""
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with async_session() as session:
        async with session.begin():
            yield session
        # Транзакция автоматически откатывается после теста


@pytest_asyncio.fixture
async def clean_db(db_session):
    """Очищаем таблицы перед конкретным тестом."""
    async with db_session.begin():
        for table in reversed(Base.metadata.sorted_tables):
            await db_session.execute(
                text(f"TRUNCATE {table.name} RESTART IDENTITY CASCADE")
            )
        await db_session.commit()
    yield


@pytest.fixture
def mock_redis():
    """Мок для Redis-клиента (для юнит- и интеграционных тестов, где требуется)."""
    mock_redis = AsyncMock()
    mock_redis.get.return_value = None
    mock_redis.set.return_value = True
    return mock_redis


@pytest.fixture
def mock_db_session():
    """Мок для сессии базы данных (для юнит-тестов)."""
    return AsyncMock()


@pytest.fixture
def client(db_session, mock_redis):
    """Фикстура для тестового клиента FastAPI с переопределением зависимостей."""

    async def override_db():
        yield db_session

    async def override_redis():
        return mock_redis

    app.dependency_overrides[db_helper.session_getter] = override_db
    app.dependency_overrides[lambda: get_redis] = override_redis
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
