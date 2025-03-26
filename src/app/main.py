from contextlib import asynccontextmanager
import subprocess
from datetime import datetime

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import ORJSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from api import router as api_router
from core.config import settings
from core.exception_handlers import (
    http_exception_handler,
    generic_exception_handler,
)
from core.logger import setup_logging
from lifespan import docker_lifespan
from utils.templates import templates

setup_logging()

app = FastAPI(lifespan=docker_lifespan)
app.include_router(api_router)
app.mount("/static", StaticFiles(directory="static"), name="static")

app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)


@app.get("/", name="home", response_class=HTMLResponse)
def index_page(request: Request):
    return templates.TemplateResponse(
        name="index.html",
        request=request,
        context={"current_year": datetime.now().year},
    )


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.run.host,
        port=settings.run.port,
        reload=True,
    )
