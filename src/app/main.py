import os
from datetime import datetime
from typing import Annotated

from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from prometheus_client import Counter
from prometheus_fastapi_instrumentator import Instrumentator

from src.app.api import router as api_router
from src.app.core.config import settings
from src.app.core.exception_handlers import (
    generic_exception_handler,
    http_exception_handler,
    validation_exception_handler,
    expired_token_exception_handler,
)
from src.app.core.exceptions import ExpiredTokenException
from src.app.core.logger import setup_logging
from src.app.core.middleware.csp_middleware import CSPMiddleware
from src.app.core.middleware.csrf_middleware import CSRFMiddleware
from src.app.core.middleware.redis_session_middleware import RedisSessionMiddleware
from src.app.lifespan import lifespan
from src.app.schemas.user import UserResponse
from src.app.services.auth import get_current_auth_user
from src.app.utils.templates import templates

setup_logging()

app = FastAPI(lifespan=lifespan)

Instrumentator().instrument(app).expose(app, endpoint="/metrics")
csrf_errors_counter = Counter(
    "csrf_errors_total",
    "Total number of CSRF errors",
    ["endpoint", "client_ip"],
)

base_dir = os.path.dirname(os.path.dirname(__file__))
static_dir = os.path.join(base_dir, "app", "static")
if os.path.exists(static_dir) and os.path.isdir(static_dir):
    app.mount("/static/", StaticFiles(directory=static_dir), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors.allow_origins,
    allow_credentials=settings.cors.allow_credentials,
    allow_methods=settings.cors.allow_methods,
    allow_headers=settings.cors.allow_headers,
    max_age=600,
)

app.add_middleware(CSPMiddleware)
app.add_middleware(CSRFMiddleware)
app.add_middleware(RedisSessionMiddleware)

app.include_router(api_router)

app.add_exception_handler(ExpiredTokenException, expired_token_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)


@app.get(
    "/",
    name="home",
    response_class=HTMLResponse,
)
def start_page(
    request: Request,
    current_user: Annotated[UserResponse, Depends(get_current_auth_user)],
):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "current_year": datetime.now().year,
            "user": current_user,
            "csp_nonce": request.state.csp_nonce,
        },
    )

