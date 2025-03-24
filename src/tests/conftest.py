import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import text  # Для выполнения SQL-запросов

from db.models import Base

# Настройки подключения к тестовой базе данных PostgreSQL
TEST_DATABASE_URL = "postgresql+asyncpg://user:1596387413@localhost:5433/test_db"


@pytest_asyncio.fixture(scope="session")
async def engine():
    """Создаем асинхронный движок для PostgreSQL."""
    # Подключаемся к серверу PostgreSQL (без указания базы данных)
    from sqlalchemy import NullPool

    temp_engine = create_async_engine(
        "postgresql+asyncpg://user:1596387413@localhost:5433/postgres",
        echo=True,
        pool_pre_ping=True,
        pool_recycle=3600,
        poolclass=NullPool,
    )

    # Проверяем, существует ли база данных test_db
    async with temp_engine.connect() as conn:
        result = await conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = 'test_db'")
        )

        if result.scalar() is None:
            # Создаем базу данных, если она не существует
            await conn.execute(text("CREATE DATABASE test_db"))
            await conn.commit()

    # Подключаемся к тестовой базе данных
    engine = create_async_engine(TEST_DATABASE_URL, echo=True)
    async with engine.begin() as conn:
        # Создаем все таблицы
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture(scope="session")
async def db_session(engine):
    """Создаем асинхронную сессию для тестов."""
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with async_session() as session:
        yield session

        # Откатываем транзакцию после завершения теста
        await session.rollback()

        # Очищаем базу данных после каждого теста
    async with engine.begin() as conn:
        for table in reversed(
            Base.metadata.sorted_tables
        ):  # удаляем в обратном порядке
            await conn.execute(
                text(f"TRUNCATE TABLE {table.name} CASCADE")
            )  # TRUNCATE быстрее DELETE
        await conn.commit()
