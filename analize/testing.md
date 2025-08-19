# Анализ тестирования - NutriCoreIQ

## Общая оценка: 3/10

### ⚠️ Критические проблемы

#### 1. Полное отсутствие тестов
```bash
# Поиск тестов в проекте
find . -name "*test*" -o -name "test_*"
# Результат: Тесты не найдены

# Исключение тестов из Docker
.dockerignore:
tests/  # Директория исключена, но не существует
```

#### 2. Настройки тестирования есть, но не используются
```toml
# pyproject.toml - зависимости для тестирования присутствуют
[tool.poetry.group.dev.dependencies]
pytest = "^8.3.5"
pytest-asyncio = "^0.25.3"
pytest-mock = "^3.14.0"
pytest-cov = "^5.0.0"  # Coverage
bcrypt = "^4.2.0"

# MyPy настроен для тестов
[[tool.mypy.overrides]]
module = ["src.app.*", "src.tests.*"]  # Но tests/ не существует
```

### ✅ Положительные аспекты конфигурации

#### 1. Хорошие инструменты подготовлены
- **pytest**: Современный тестовый фреймворк
- **pytest-asyncio**: Поддержка async/await тестов
- **pytest-mock**: Мокирование зависимостей
- **pytest-cov**: Измерение покрытия кода

#### 2. Тестовая конфигурация БД
```python
# core/config.py - поддержка тестовой БД
class DatabaseConfig(BaseModel):
    test_url: Optional[PostgresDsn] = None
    is_test: bool = False

    @property
    def effective_db_url(self) -> PostgresDsn:
        if self.is_test and self.test_url:
            return self.test_url  # Отдельная БД для тестов
```

### 🔧 Рекомендуемая структура тестов

#### 1. Создать базовую структуру
```
tests/
├── conftest.py              # Фикстуры
├── unit/                    # Модульные тесты
│   ├── test_models.py
│   ├── test_schemas.py
│   ├── test_crud.py
│   └── test_utils.py
├── integration/             # Интеграционные тесты
│   ├── test_auth_flow.py
│   ├── test_product_api.py
│   └── test_user_api.py
├── functional/              # Функциональные тесты
│   ├── test_registration.py
│   ├── test_search.py
│   └── test_profile.py
└── load/                    # Нагрузочные тесты
    └── locustfile.py
```

#### 2. Базовые фикстуры (conftest.py)
```python
import pytest
import asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from src.app.core.app import create_app
from src.app.core.config import settings
from src.app.models import Base
from src.app.core import db_helper

# Настройка тестовой БД
TEST_DATABASE_URL = "postgresql+asyncpg://test_user:test_pass@localhost/test_db"

@pytest.fixture(scope="session")
def event_loop():
    """Создание event loop для всей сессии тестирования"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def test_engine():
    """Тестовый движок БД"""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)

    # Создание таблиц
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Очистка после тестов
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()

@pytest.fixture
async def db_session(test_engine):
    """Сессия БД для каждого теста"""
    async_session_maker = sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session_maker() as session:
        yield session
        await session.rollback()  # Откат изменений после теста

@pytest.fixture
async def test_app():
    """Тестовое приложение FastAPI"""
    app = create_app()
    # Переопределение зависимостей для тестов
    return app

@pytest.fixture
async def client(test_app):
    """HTTP клиент для тестирования API"""
    async with AsyncClient(app=test_app, base_url="http://test") as ac:
        yield ac

@pytest.fixture
async def test_user(db_session):
    """Тестовый пользователь"""
    from src.app.crud.user import create_user
    from src.app.schemas.user import UserCreate

    user_data = UserCreate(
        username="testuser",
        email="test@example.com",
        password="testpassword123"
    )

    user = await create_user(db_session, user_data)
    return user

@pytest.fixture
async def authenticated_client(client, test_user):
    """Аутентифицированный клиент"""
    # Логин
    response = await client.post("/api/v1/auth/login", data={
        "username": test_user.username,
        "password": "testpassword123"
    })

    # Извлечение токена из куки
    access_token = response.cookies.get("access_token")
    client.cookies["access_token"] = access_token

    return client
```

#### 3. Модульные тесты моделей
```python
# tests/unit/test_models.py
import pytest
from sqlalchemy.exc import IntegrityError

from src.app.models import User, Product, ProductGroup

class TestUserModel:
    async def test_user_creation(self, db_session):
        """Тест создания пользователя"""
        user = User(
            username="testuser",
            email="test@example.com",
            hashed_password=b"hashed_password"
        )

        db_session.add(user)
        await db_session.commit()

        assert user.id is not None
        assert user.uid is not None
        assert user.created_at is not None
        assert user.is_active is True
        assert user.role == "user"

    async def test_user_unique_constraints(self, db_session):
        """Тест уникальности username и email"""
        user1 = User(
            username="testuser",
            email="test@example.com",
            hashed_password=b"hashed"
        )

        user2 = User(
            username="testuser",  # Дублирующий username
            email="test2@example.com",
            hashed_password=b"hashed"
        )

        db_session.add(user1)
        await db_session.commit()

        db_session.add(user2)
        with pytest.raises(IntegrityError):
            await db_session.commit()

class TestProductModel:
    async def test_product_with_search_vector(self, db_session):
        """Тест продукта с поисковым вектором"""
        group = ProductGroup(name="Молочные продукты")
        db_session.add(group)
        await db_session.flush()

        product = Product(
            title="Молоко коровье",
            group_id=group.id
        )

        db_session.add(product)
        await db_session.commit()

        assert product.id is not None
        assert product.search_vector is not None
```

#### 4. Тесты CRUD операций
```python
# tests/unit/test_crud.py
import pytest
from fastapi import HTTPException

from src.app.crud.user import (
    create_user, get_user_by_uid, get_user_by_email, get_user_by_name
)
from src.app.schemas.user import UserCreate

class TestUserCRUD:
    async def test_create_user_success(self, db_session):
        """Тест успешного создания пользователя"""
        user_data = UserCreate(
            username="newuser",
            email="newuser@example.com",
            password="securepassword123"
        )

        created_user = await create_user(db_session, user_data)

        assert created_user.username == user_data.username
        assert created_user.email == user_data.email
        # Пароль не должен возвращаться в response

    async def test_get_user_by_uid(self, db_session, test_user):
        """Тест получения пользователя по UID"""
        user = await get_user_by_uid(db_session, test_user.uid)

        assert user.id == test_user.id
        assert user.username == test_user.username

    async def test_get_user_by_nonexistent_uid(self, db_session):
        """Тест получения несуществующего пользователя"""
        with pytest.raises(HTTPException) as exc_info:
            await get_user_by_uid(db_session, "nonexistent-uid")

        assert exc_info.value.status_code == 404

    async def test_get_user_by_email(self, db_session, test_user):
        """Тест поиска пользователя по email"""
        user = await get_user_by_email(db_session, test_user.email)

        assert user is not None
        assert user.email == test_user.email

    async def test_get_user_by_email_not_found(self, db_session):
        """Тест поиска несуществующего email"""
        user = await get_user_by_email(db_session, "nonexistent@example.com")

        assert user is None
```

#### 5. Интеграционные тесты API
```python
# tests/integration/test_auth_flow.py
import pytest

class TestAuthFlow:
    async def test_registration_flow(self, client):
        """Тест полного процесса регистрации"""
        # Регистрация
        registration_data = {
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "securepassword123"
        }

        response = await client.post("/api/v1/auth/register", json=registration_data)

        assert response.status_code == 201
        data = response.json()
        assert data["username"] == registration_data["username"]
        assert data["email"] == registration_data["email"]
        assert "password" not in data

    async def test_login_flow(self, client, test_user):
        """Тест процесса входа"""
        login_data = {
            "username": test_user.username,
            "password": "testpassword123"
        }

        response = await client.post("/api/v1/auth/login", data=login_data)

        assert response.status_code == 200
        assert "access_token" in response.cookies

        # Проверка защищенного эндпоинта
        profile_response = await client.get("/api/v1/user/me")
        assert profile_response.status_code == 200

    async def test_logout_flow(self, authenticated_client):
        """Тест выхода из системы"""
        # Проверяем что клиент аутентифицирован
        response = await authenticated_client.get("/api/v1/user/me")
        assert response.status_code == 200

        # Выход
        logout_response = await authenticated_client.post("/api/v1/auth/logout")
        assert logout_response.status_code == 200

        # Проверяем что токен недействителен
        me_response = await authenticated_client.get("/api/v1/user/me")
        assert me_response.status_code == 401

class TestProductAPI:
    async def test_product_search(self, authenticated_client):
        """Тест поиска продуктов"""
        response = await authenticated_client.get(
            "/api/v1/product/search?query=молоко"
        )

        assert response.status_code == 200
        data = response.json()
        assert "exact_match" in data
        assert "suggestions" in data

    async def test_product_search_validation(self, authenticated_client):
        """Тест валидации поискового запроса"""
        # Слишком короткий запрос
        response = await authenticated_client.get(
            "/api/v1/product/search?query=a"
        )

        assert response.status_code == 422  # Validation error

    async def test_product_details(self, authenticated_client):
        """Тест получения деталей продукта"""
        # Предполагаем что продукт с ID 1 существует
        response = await authenticated_client.get("/api/v1/product/1")

        if response.status_code == 200:
            # Проверяем структуру ответа
            content = response.content.decode()
            assert "<!DOCTYPE html>" in content  # HTML response

    async def test_add_pending_product(self, authenticated_client):
        """Тест добавления продукта в очередь"""
        pending_data = {"name": "Новый продукт"}

        response = await authenticated_client.post(
            "/api/v1/product/pending",
            json=pending_data
        )

        assert response.status_code in [200, 201]

        # Повторное добавление должно вызвать ошибку
        duplicate_response = await authenticated_client.post(
            "/api/v1/product/pending",
            json=pending_data
        )

        assert duplicate_response.status_code == 400
```

#### 6. Функциональные тесты
```python
# tests/functional/test_user_journey.py
import pytest

class TestUserJourney:
    async def test_complete_user_registration_to_product_search(self, client):
        """Тест полного пути пользователя: регистрация → поиск"""

        # 1. Регистрация
        registration_data = {
            "username": "journeyuser",
            "email": "journey@example.com",
            "password": "journeypass123"
        }

        reg_response = await client.post("/api/v1/auth/register", json=registration_data)
        assert reg_response.status_code == 201

        # 2. Логин
        login_response = await client.post("/api/v1/auth/login", data={
            "username": registration_data["username"],
            "password": registration_data["password"]
        })
        assert login_response.status_code == 200

        # 3. Получение профиля
        profile_response = await client.get("/api/v1/user/me")
        assert profile_response.status_code == 200

        # 4. Поиск продуктов
        search_response = await client.get("/api/v1/product/search?query=молоко")
        assert search_response.status_code == 200

        # 5. Обновление подписки
        unsub_response = await client.post("/api/v1/user/unsubscribe")
        assert unsub_response.status_code == 200

    async def test_unauthenticated_access_protection(self, client):
        """Тест защиты от неавторизованного доступа"""
        protected_endpoints = [
            "/api/v1/user/me",
            "/api/v1/user/profile",
            "/api/v1/product/search",
            "/api/v1/product/pending"
        ]

        for endpoint in protected_endpoints:
            response = await client.get(endpoint)
            # Должен перенаправлять на главную или возвращать 401
            assert response.status_code in [200, 401, 302]
```

#### 7. Настройка pytest.ini
```ini
# pytest.ini
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts =
    --strict-markers
    --strict-config
    --verbose
    --tb=short
    --cov=src/app
    --cov-report=html
    --cov-report=term-missing
    --cov-fail-under=80
asyncio_mode = auto
markers =
    slow: marks tests as slow
    integration: marks tests as integration
    unit: marks tests as unit
    functional: marks tests as functional
```

### 🚀 Запуск тестов

#### 1. Команды для разработки
```bash
# Все тесты
poetry run pytest

# Только unit тесты
poetry run pytest tests/unit/ -v

# С покрытием
poetry run pytest --cov=src/app --cov-report=html

# Быстрые тесты (исключить медленные)
poetry run pytest -m "not slow"

# Интеграционные тесты
poetry run pytest tests/integration/ -v

# Один конкретный тест
poetry run pytest tests/unit/test_models.py::TestUserModel::test_user_creation -v
```

#### 2. CI/CD интеграция
```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:17
        env:
          POSTGRES_PASSWORD: test_pass
          POSTGRES_USER: test_user
          POSTGRES_DB: test_db
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432

      redis:
        image: redis:latest
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 6379:6379

    steps:
    - uses: actions/checkout@v3

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.13'

    - name: Install Poetry
      uses: snok/install-poetry@v1

    - name: Install dependencies
      run: poetry install

    - name: Run tests
      run: poetry run pytest --cov=src/app --cov-report=xml
      env:
        DATABASE_URL: postgresql+asyncpg://test_user:test_pass@localhost/test_db
        REDIS_URL: redis://localhost:6379

    - name: Upload coverage
      uses: codecov/codecov-action@v3
```

### 📊 Цели покрытия тестами

#### Минимальные требования
- **Unit тесты**: 90% покрытие
- **Integration тесты**: Все API endpoints
- **Functional тесты**: Основные user journeys
- **Security тесты**: Все аутентификация flows

#### Приоритетные области для тестирования
1. **Критично**: Аутентификация, авторизация, CRUD пользователей
2. **Высоко**: Поиск продуктов, валидация данных
3. **Средне**: Middleware, утилиты, кэширование
4. **Низко**: Статические файлы, шаблоны

### 🎯 План внедрения тестирования

#### Фаза 1 (1 неделя)
- Создать базовую структуру тестов
- Написать конфигурационные файлы
- Создать основные фикстуры

#### Фаза 2 (2 недели)
- Unit тесты для моделей и CRUD
- Тесты аутентификации/авторизации
- Базовые API тесты

#### Фаза 3 (1 неделя)
- Интеграционные тесты API
- Функциональные тесты user journeys
- Настройка CI/CD

#### Фаза 4 (2 недели)
- Performance тесты
- Security тесты
- Доведение покрытия до целевых значений

**Итог**: Проект критически нуждается в тестировании. Несмотря на хорошую подготовку инструментов, полное отсутствие тестов создает серьезные риски для надежности и качества системы. Необходимо срочно внедрить базовое тестирование.
