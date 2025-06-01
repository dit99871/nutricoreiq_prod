import os
import sys
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import text
from fastapi.testclient import TestClient

# Динамически добавляем src в sys.path
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src"))
if src_path not in sys.path:
    sys.path.insert(0, src_path)
print("Updated sys.path in conftest.py:", sys.path)

from src.app.main import app
from src.app.db.models import Base
from src.app.core.config import settings
from unittest.mock import AsyncMock

# Определяем URL и echo для тестов
TEST_DATABASE_URL = settings.db.test_url or settings.db.url
SQLALCHEMY_ECHO = (
    settings.db.test_echo if settings.db.test_echo is not None else settings.db.echo
)


@pytest_asyncio.fixture(scope="session")
async def engine():
    """Создаем асинхронный движок для PostgreSQL и тестовую базу данных."""
    from sqlalchemy import NullPool

    # Подключаемся к серверу PostgreSQL (к базе 'postgres') для создания тестовой БД
    default_db_url = TEST_DATABASE_URL.replace("test_nutricoreiq", "postgres")
    temp_engine = create_async_engine(
        default_db_url,
        echo=SQLALCHEMY_ECHO,
        pool_pre_ping=True,
        pool_recycle=3600,
        poolclass=NullPool,
    )

    # Проверяем и создаем тестовую базу данных, если она не существует
    async with temp_engine.connect() as conn:
        try:
            await conn.execute(text("COMMIT"))
            result = await conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = 'test_nutricoreiq'")
            )
            if result.scalar() is None:
                await conn.execute(text("CREATE DATABASE test_nutricoreiq"))
                await conn.execute(text("COMMIT"))
        except Exception as e:
            print(f"Ошибка при создании базы данных: {e}")
            raise
        finally:
            await temp_engine.dispose()

    # Создаем движок для тестовой базы данных
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=SQLALCHEMY_ECHO,
        pool_pre_ping=True,
        pool_recycle=3600,
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


@pytest.fixture(scope="function")
def client(db_session):
    """Фикстура для тестового клиента FastAPI с переопределением зависимостей."""

    async def override_db():
        yield db_session

    app.dependency_overrides[lambda: None] = override_db  # Замените на вашу зависимость
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True, scope="session")
def setup_test_environment():
    """Настраиваем окружение для тестов."""
    os.environ["ENV"] = "test"
    os.environ["TESTING"] = "true"
    yield
    os.environ.pop("ENV", None)
    os.environ.pop("TESTING", None)


@pytest.fixture
def mock_redis(mocker):
    """Фикстура для мокинга Redis с базовыми методами."""
    mock_redis = AsyncMock()
    mock_redis.get.return_value = None
    mock_redis.set.return_value = True
    mocker.patch("src.app.core.redis.get_redis", return_value=mock_redis)
    return mock_redis


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
