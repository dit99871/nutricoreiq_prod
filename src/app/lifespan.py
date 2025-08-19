from contextlib import asynccontextmanager

from fastapi import FastAPI
from tenacity import retry, stop_after_attempt, wait_fixed

from src.app.core import broker
from src.app.core import db_helper
from src.app.core.logger import get_logger
from src.app.core.redis import init_redis, close_redis

log = get_logger("lifespan")


@retry(stop=stop_after_attempt(4), wait=wait_fixed(15))
async def check_rabbitmq():
    try:
        await broker.startup()
    except Exception as e:
        log.error(f"RabbitMQ not ready: {e}")
        raise


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("Starting application lifespan...")

    try:
        log.info("Initializing Redis connection...")
        await init_redis()
        log.info("Redis connection initialized successfully")
    except Exception as e:
        log.error(f"Failed to initialize Redis: {e}")
        raise

    if not broker.is_worker_process:
        try:
            log.info("Checking RabbitMQ connection...")
            # await check_rabbitmq()
            log.info("RabbitMQ connection established successfully")
        except Exception as e:
            log.error(f"Failed to connect to RabbitMQ: {e}")
            raise

    log.info("Application startup completed successfully")
    try:
        yield
    finally:
        log.info("Shutting down application...")
        await close_redis()
        await db_helper.dispose()
        if not broker.is_worker_process:
            await broker.shutdown()
        log.info("Application shutdown completed")
