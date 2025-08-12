import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from prometheus_fastapi_instrumentator import Instrumentator

from src.app.core.middleware import setup_middleware
from src.app.core.exception_handlers import setup_exception_handlers
from src.app.routers import routers
from src.app.lifespan import lifespan


def create_app() -> FastAPI:
    """
    Создает FastAPI приложение.

    1. Создает приложение FastAPI.
    2. Настраивает Prometheus.
    3. Монтирует статические файлы.
    4. Настраивает middleware.
    5. Настраивает обработчики исключений.
    6. Подключает роутеры.

    :return: FastAPI приложение.
    :rtype: FastAPI
    """
    app = FastAPI(lifespan=lifespan)

    # Настройка Prometheus
    Instrumentator().instrument(app).expose(app, endpoint="/metrics")

    # Монтирование статических файлов
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    static_dir = os.path.join(base_dir, "app", "static")
    if os.path.exists(static_dir) and os.path.isdir(static_dir):
        app.mount("/static/", StaticFiles(directory=static_dir), name="static")

    # Настройка middleware
    setup_middleware(app)

    # Настройка обработчиков исключений
    setup_exception_handlers(app)

    # Подключение роутеров
    app.include_router(routers)

    return app
