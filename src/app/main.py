from datetime import datetime

from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.responses import HTMLResponse, ORJSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

from api import router as api_router
from core.config import settings
from core.exception_handlers import (
    http_exception_handler,
    generic_exception_handler,
)
from core.logger import setup_logging
from lifespan import docker_lifespan
from services.user import get_current_auth_user
from utils.security import generate_csrf_token, generate_csp_nonce
from utils.templates import templates

setup_logging()

app = FastAPI(
    lifespan=docker_lifespan,
    default_response_class=ORJSONResponse,
)
app.include_router(api_router)
app.mount(
    "/static",
    StaticFiles(directory="static"),
    name="static",
)

app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)


@app.get("/", name="home", response_class=HTMLResponse)
def start_page(
    request: Request,
    current_user: str | None = Depends(get_current_auth_user),
):
    return templates.TemplateResponse(
        name="index.html",
        request=request,
        context={
            "current_year": datetime.now().year,
            "user": current_user or None,
            "csrf_token": generate_csrf_token(),
            "csp_nonce": generate_csp_nonce(),
        },
    )


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.run.host,
        port=settings.run.port,
        reload=True,
    )
