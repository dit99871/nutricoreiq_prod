from contextlib import asynccontextmanager
import subprocess

from fastapi import FastAPI


@asynccontextmanager
async def docker_lifespan(app: FastAPI):
    subprocess.run(
        ["docker-compose", "-f", "docker-compose.dev.yml", "up", "-d"], check=True
    )
    yield
