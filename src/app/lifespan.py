from contextlib import asynccontextmanager

from fastapi import FastAPI
from tenacity import retry, stop_after_attempt, wait_fixed

from src.app.core import broker
from src.app.core.logger import get_logger
from src.app.core.redis import init_redis, close_redis
from src.app.db import db_helper

log = get_logger("lifespan")


@retry(stop=stop_after_attempt(15), wait=wait_fixed(4))
async def check_rabbitmq():
    try:
        await broker.startup()
    except Exception as e:
        log.error(f"RabbitMQ not ready: {e}")
        raise


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not broker.is_worker_process:
        await check_rabbitmq()
    try:
        yield
    finally:
        await close_redis()
        await db_helper.dispose()
        if not broker.is_worker_process:
            await broker.shutdown()
