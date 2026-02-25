__all__ = ("broker",)

import logging

import taskiq_fastapi
from taskiq import TaskiqEvents, TaskiqState
from taskiq_aio_pika import AioPikaBroker

from src.app.core.config import settings
from src.app.core.services.sentry import init_sentry

log = logging.getLogger("taskiq_broker")

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
        # Логирование уже настроено в main.py через setup_logging()
        log.info("Worker startup complete, got state: %s", state)
