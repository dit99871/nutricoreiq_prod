__all__ = ("broker",)

import taskiq_fastapi
from taskiq import TaskiqEvents, TaskiqState
from taskiq_aio_pika import AioPikaBroker

from src.app.core.config import settings
from src.app.core.logger import get_logger
from src.app.core.services.sentry import init_sentry

log = get_logger("taskiq_broker_service")

if settings.env.env == "prod":
    init_sentry()

    broker = AioPikaBroker(
        url=str(settings.taskiq.url),
    )

    taskiq_fastapi.init(
        broker,
        "src.app.main:app",
    )

    @broker.on_event(TaskiqEvents.WORKER_STARTUP)
    async def on_worker_startup(state: TaskiqState) -> None:
        log.info("Запуск worker завершен. Состояние: %s", state)
