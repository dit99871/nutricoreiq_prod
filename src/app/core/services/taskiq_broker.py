"""Инициализация Taskiq broker для фоновых задач."""

__all__ = ("broker",)

import taskiq_fastapi
from taskiq import TaskiqEvents, TaskiqState
from taskiq_aio_pika import AioPikaBroker

from src.app.core.config import settings
from src.app.core.logger import get_logger

log = get_logger("taskiq_broker_service")

if settings.env.env == "prod":
    # Sentry инициализируется в main.py, а не здесь, чтобы избежать циклических импортов
    broker = AioPikaBroker(
        url=str(settings.taskiq.url),
    )

    taskiq_fastapi.init(
        broker,
        "src.app.main:app",
    )

    @broker.on_event(TaskiqEvents.WORKER_STARTUP)
    async def on_worker_startup(state: TaskiqState) -> None:
        """Логирует факт успешного старта воркера Taskiq."""

        log.info("Запуск worker завершен. Состояние: %s", state)
else:
    # В development режиме используем dummy broker
    from src.app.core.services.dummy_broker import DummyBroker
    broker = DummyBroker()
