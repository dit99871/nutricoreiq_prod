from contextlib import asynccontextmanager
import subprocess

from fastapi import FastAPI

from src.app.core.redis import init_redis, close_redis
from src.app.core.logger import get_logger

log = get_logger("lifespan")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # subprocess.run(
    #     ["docker-compose", "-f", "docker-compose.dev.yml", "up", "-d"],
    #     check=True,
    # )
    await init_redis()
    try:
        yield
    finally:
        await close_redis()
