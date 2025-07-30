from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.app.core.redis import init_redis, close_redis
from src.app.core import broker
from src.app.db import db_helper


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_redis()

    if not broker.is_worker_process:
        await broker.startup()

    try:
        yield
    finally:
        await close_redis()
        await db_helper.dispose()
        if not broker.is_worker_process:
            await broker.shutdown()
