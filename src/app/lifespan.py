from contextlib import asynccontextmanager
import subprocess

from fastapi import FastAPI

from src.app.core.logger import get_logger
from src.app.core.redis import init_redis, close_redis
from src.app.core import broker
from src.app.db import db_helper

log = get_logger("lifespan")


@asynccontextmanager
async def lifespan(app: FastAPI):
    subprocess.run(
        ["docker-compose", "-f", "docker-compose.dev.yml", "up", "-d"],
        check=True,
    )
    await broker.startup()
    await init_redis()
    try:
        yield
    finally:
        await close_redis()
        await broker.shutdown()
        await db_helper.dispose()
