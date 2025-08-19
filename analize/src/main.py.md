# Анализ src/app/main.py

## Архитектурные проблемы

### 1. Нарушение принципа разделения ответственности (строки 19-36)
```python
# ПРОБЛЕМА: Обработчик маршрута в main.py вместо роутера
@app.get("/", name="home", response_class=HTMLResponse)
def start_page(
    request: Request,
    current_user: Annotated[UserResponse, Depends(get_current_auth_user)],
):
    return templates.TemplateResponse(...)
```

**Проблемы:**
- Main.py должен быть только точкой входа
- Бизнес-логика не должна быть в main.py
- Нарушает Clean Architecture

**Исправление:**
```python
# src/app/main.py - только создание приложения
from src.app.core.app import create_app
from src.app.core.logger import setup_logging

setup_logging()
app: FastAPI = create_app()

# Переместить маршрут в src/app/routers/info.py
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["Info"])

@router.get("/", name="home", response_class=HTMLResponse)
async def start_page(
    request: Request,
    current_user: Annotated[UserResponse, Depends(get_current_auth_user)],
):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "current_year": datetime.now().year,
            "user": current_user,
            "csp_nonce": request.state.csp_nonce,
        },
    )
```

### 2. Отсутствие обработки ошибок при запуске
```python
# ПРОБЛЕМА: Нет обработки ошибок инициализации
setup_logging()
app: FastAPI = create_app()

# УЛУЧШЕНИЕ: Добавить обработку ошибок
import sys
from src.app.core.logger import get_logger

log = get_logger("main")

try:
    setup_logging()
    log.info("Logging initialized successfully")

    app: FastAPI = create_app()
    log.info("FastAPI application created successfully")

except Exception as e:
    print(f"Failed to initialize application: {e}")
    sys.exit(1)
```

### 3. Отсутствие health check endpoints
```python
# ДОБАВИТЬ: Health check в main.py или отдельном роутере
@app.get("/health", include_in_schema=False)
async def health_check():
    """Simple health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.get("/ready", include_in_schema=False)
async def readiness_check(
    session: Annotated[AsyncSession, Depends(db_helper.session_getter)],
    redis: Redis = Depends(get_redis),
):
    """Readiness check that verifies dependencies"""
    try:
        # Проверка БД
        await session.execute(text("SELECT 1"))

        # Проверка Redis
        await redis.ping()

        return {"status": "ready", "timestamp": datetime.now().isoformat()}
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail={"status": "not_ready", "error": str(e)}
        )
```

## Рекомендации по улучшению

### 1. Разделить ответственность
```python
# src/app/main.py - минимальная точка входа
"""
FastAPI application entry point.
"""
from src.app.core.app import create_app
from src.app.core.logger import setup_logging, get_logger

__version__ = "0.1.0"

# Инициализация логирования
setup_logging()
log = get_logger("main")

# Создание приложения
try:
    app = create_app()
    log.info("Application initialized successfully, version=%s", __version__)
except Exception as e:
    log.critical("Failed to initialize application: %s", e)
    raise

# Переместить маршруты в src/app/routers/pages.py
from datetime import datetime
from typing import Annotated
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse

from src.app.core.utils import templates
from src.app.schemas.user import UserResponse
from src.app.core.services.auth import get_current_auth_user

router = APIRouter(tags=["Pages"])

@router.get("/", name="home", response_class=HTMLResponse)
async def home_page(
    request: Request,
    current_user: Annotated[UserResponse, Depends(get_current_auth_user)],
):
    """Главная страница приложения"""
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "current_year": datetime.now().year,
            "user": current_user,
            "csp_nonce": request.state.csp_nonce,
        },
    )

# И подключить в src/app/routers/__init__.py
routers.include_router(pages_router)
```

### 2. Добавить startup события
```python
# src/app/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    log.info("Application starting up...")

    # Проверка зависимостей при старте
    await check_dependencies()

    log.info("Application ready to accept requests")
    yield

    # Shutdown
    log.info("Application shutting down...")

async def check_dependencies():
    """Проверка критических зависимостей при старте"""
    from src.app.core import db_helper
    from src.app.core.redis import get_redis

    try:
        # Проверка БД
        async with db_helper.session_getter() as session:
            await session.execute(text("SELECT 1"))
        log.info("Database connection verified")

        # Проверка Redis
        redis = await get_redis().__anext__()
        await redis.ping()
        log.info("Redis connection verified")

    except Exception as e:
        log.critical("Dependency check failed: %s", e)
        raise

# В create_app добавить lifespan
app = FastAPI(lifespan=lifespan)
```

### 3. Добавить метаданные приложения
```python
# src/app/main.py
from src.app.core.app import create_app
from src.app.core.config import settings

# Метаданные приложения
APP_METADATA = {
    "title": "NutriCoreIQ API",
    "description": "API для анализа питательной ценности продуктов",
    "version": "0.1.0",
    "contact": {
        "name": "NutriCoreIQ Support",
        "email": "dit99871@gmail.com",
    },
    "license_info": {
        "name": "MIT",
    },
}

# Создание приложения с метаданными
try:
    app = create_app(**APP_METADATA)
    log.info("Application '%s' v%s initialized", APP_METADATA["title"], APP_METADATA["version"])
except Exception as e:
    log.critical("Failed to initialize application: %s", e)
    raise
```

## Полное исправленное решение

```python
# src/app/main.py
"""
NutriCoreIQ FastAPI Application Entry Point.

Создает и настраивает FastAPI приложение для анализа питательной ценности продуктов.
"""
import sys
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis

from src.app.core.app import create_app
from src.app.core.logger import setup_logging, get_logger
from src.app.core import db_helper
from src.app.core.redis import get_redis

__version__ = "0.1.0"

# Инициализация логирования
try:
    setup_logging()
    log = get_logger("main")
    log.info("Logging system initialized")
except Exception as e:
    print(f"CRITICAL: Failed to initialize logging: {e}")
    sys.exit(1)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управление жизненным циклом приложения"""
    # Startup
    log.info("Application starting up...")

    try:
        await check_dependencies()
        log.info("All dependencies verified, application ready")
    except Exception as e:
        log.critical("Dependency check failed: %s", e)
        raise

    yield

    # Shutdown
    log.info("Application shutting down...")


async def check_dependencies():
    """Проверка критических зависимостей при старте"""
    try:
        # Проверка БД
        async with db_helper.session_getter() as session:
            await session.execute(text("SELECT 1"))
        log.info("Database connection verified")

        # Проверка Redis
        async for redis in get_redis():
            await redis.ping()
            break
        log.info("Redis connection verified")

    except Exception as e:
        log.error("Dependency check failed: %s", e)
        raise


# Создание приложения
try:
    app = create_app()
    app.router.lifespan_context = lifespan

    log.info("FastAPI application created successfully, version=%s", __version__)
except Exception as e:
    log.critical("Failed to create FastAPI application: %s", e)
    sys.exit(1)


# Health check endpoints
@app.get("/health", include_in_schema=False, tags=["Health"])
async def health_check():
    """Простая проверка здоровья приложения"""
    return {
        "status": "healthy",
        "version": __version__,
        "timestamp": datetime.now().isoformat()
    }


@app.get("/ready", include_in_schema=False, tags=["Health"])
async def readiness_check(
    session: AsyncSession = Depends(db_helper.session_getter),
    redis: Redis = Depends(get_redis),
):
    """Проверка готовности приложения и зависимостей"""
    try:
        # Проверка БД
        await session.execute(text("SELECT 1"))

        # Проверка Redis
        await redis.ping()

        return {
            "status": "ready",
            "version": __version__,
            "timestamp": datetime.now().isoformat(),
            "dependencies": {
                "database": "healthy",
                "redis": "healthy"
            }
        }
    except Exception as e:
        log.error("Readiness check failed: %s", e)
        raise HTTPException(
            status_code=503,
            detail={
                "status": "not_ready",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
        )


if __name__ == "__main__":
    import uvicorn

    log.info("Starting application in development mode")
    uvicorn.run(
        "src.app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_config=None  # Используем наше логирование
    )
```

```python
# src/app/routers/pages.py - новый файл для страниц
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse

from src.app.core.utils import templates
from src.app.schemas.user import UserResponse
from src.app.core.services.auth import get_current_auth_user

router = APIRouter(tags=["Pages"])


@router.get("/", name="home", response_class=HTMLResponse)
async def home_page(
    request: Request,
    current_user: Annotated[UserResponse, Depends(get_current_auth_user)],
):
    """Главная страница приложения"""
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "current_year": datetime.now().year,
            "user": current_user,
            "csp_nonce": request.state.csp_nonce,
        },
    )
```

## Приоритет исправлений

1. **Высокий**: Переместить маршрут из main.py в отдельный роутер
2. **Средний**: Добавить health check endpoints
3. **Средний**: Добавить обработку ошибок инициализации
4. **Низкий**: Добавить lifespan события и проверку зависимостей
