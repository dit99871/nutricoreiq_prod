from contextlib import asynccontextmanager
import subprocess

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import ORJSONResponse

from api import router as api_router
from core.config import settings
from core.logger import setup_logging

setup_logging()


@asynccontextmanager
async def lifespan_docker(app: FastAPI):
    subprocess.run(["docker-compose", "up", "-d"], check=True)
    yield


app = FastAPI(lifespan=lifespan_docker)
app.include_router(api_router)


@app.exception_handler(HTTPException)
def http_exception_handler(request: Request, exc: HTTPException):
    return ORJSONResponse(
        status_code=exc.status_code,
        content={"message": exc.detail},
    )


@app.exception_handler(Exception)
def generic_exception_handler(request: Request, exc: Exception):
    return ORJSONResponse(
        status_code=500,
        content={"message": "Internal Server Error", "detail": str(exc)},
    )


@app.get("/", response_class=ORJSONResponse)
def main():
    return {"message": "Hi, searching!"}


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.run.host,
        port=settings.run.port,
        reload=True,
    )
