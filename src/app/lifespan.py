from contextlib import asynccontextmanager
import subprocess

from fastapi import FastAPI

from src.app.core.redis import init_redis, close_redis
from src.app.core.logger import get_logger

log = get_logger("lifespan")


@asynccontextmanager
async def lifespan(app: FastAPI):
    subprocess.run(
        ["docker-compose", "-f", "docker-compose.dev.yml", "up", "-d"],
        check=True,
    )
    await init_redis()
    log.info("Application startup complete")
    try:
        yield
    finally:
        log.info("Shutting down application...")
        await close_redis()
        log.info("All resources closed")
