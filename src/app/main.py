from datetime import datetime

from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, ORJSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

from src.app.api import router as api_router
from src.app.core.config import settings
from src.app.core.exception_handlers import (
    http_exception_handler,
    generic_exception_handler,
)
from src.app.core.logger import setup_logging
from src.app.lifespan import docker_lifespan
from src.app.services.auth import get_current_auth_user
from src.app.utils.security import generate_csrf_token, generate_csp_nonce
from src.app.utils.templates import templates

setup_logging()

app = FastAPI(
    lifespan=docker_lifespan,
    default_response_class=ORJSONResponse,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors.allow_origins,
    allow_credentials=settings.cors.allow_credentials,
    allow_methods=settings.cors.allow_methods,
    allow_headers=settings.cors.allow_headers,
    max_age=600,
)
app.include_router(api_router)
# Монтирование статических файлов откладывается
if __name__ == "__main__":
    app.mount("/static/", StaticFiles(directory="src/app/static"), name="static")
    uvicorn.run("main:app", host=settings.run.host, port=settings.run.port, reload=True)
else:
    # Для тестов или импорта можно не монтировать
    pass

app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)


@app.get("/", name="home", response_class=HTMLResponse)
def start_page(
    request: Request,
    current_user: str | None = Depends(get_current_auth_user),
):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "current_year": datetime.now().year,
            "user": current_user,
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
