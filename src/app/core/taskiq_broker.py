__all__ = ("broker",)

import logging

import taskiq_fastapi
from taskiq import TaskiqEvents, TaskiqState
from taskiq_aio_pika import AioPikaBroker

from src.app.core.config import settings

log = logging.getLogger("taskiq_broker")

broker = AioPikaBroker(
    url=str(settings.taskiq.url),
)

taskiq_fastapi.init(
    broker,
    "src.app.main:app",
)


@broker.on_event(TaskiqEvents.WORKER_STARTUP)
async def on_worker_startup(state: TaskiqState) -> None:
    logging.basicConfig(
        level=settings.logging.log_level_value,
        format=settings.taskiq.log_format,
        datefmt=settings.logging.log_date_format,
    )
    log.info("Worker startup complete, got state: %s", state)
