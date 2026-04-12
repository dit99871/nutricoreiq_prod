import os

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from prometheus_fastapi_instrumentator import Instrumentator

from src.app.core.exception_handlers import setup_exception_handlers
from src.app.core.logger import setup_logging
from src.app.core.middleware import setup_middleware
from src.app.core.services.limiter import limiter
from src.app.lifespan import lifespan
from src.app.routers import routers


def create_app() -> FastAPI:
    """
    Создает FastAPI приложение.

    1. Настраивает логирование.
    2. Создает приложение FastAPI.
    3. Настраивает Prometheus.
    4. Монтирует статические файлы.
    5. Настраивает middleware.
    6. Настраивает обработчики исключений.
    7. Подключает роутеры.

    :return: FastAPI приложение.
    :rtype: FastAPI
    """

    setup_logging()
    app = FastAPI(lifespan=lifespan)

    # настройка prometheus
    Instrumentator().instrument(app).expose(app, endpoint="/metrics")

    # монтирование статических файлов
    base_dir = os.path.dirname(os.path.dirname(str(os.path.dirname(__file__))))
    static_dir = os.path.join(str(base_dir), "app", "static")
    if os.path.exists(static_dir) and os.path.isdir(static_dir):
        app.mount("/static/", StaticFiles(directory=str(static_dir)), name="static")

    # настройка обработчиков исключений
    setup_exception_handlers(app)

    # настройка мидлвари
    setup_middleware(app)

    # подключение роутеров
    app.include_router(routers)

    # подключение лимитера
    app.state.limiter = limiter

    return app
