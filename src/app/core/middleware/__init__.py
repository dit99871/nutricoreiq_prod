from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sentry_sdk.integrations.asgi import SentryAsgiMiddleware

from src.app.core.config import settings
from .csp_middleware import CSPMiddleware
from .csrf_middleware import CSRFMiddleware
from .redis_session_middleware import RedisSessionMiddleware

__all__ = ("setup_middleware",)


def setup_middleware(app: FastAPI) -> None:
    """
    Add middleware to the FastAPI application.

    This function adds various middleware to the provided FastAPI application.
    The middleware includes CORSMiddleware, SentryAsgiMiddleware, RedisSessionMiddleware,
    CSPMiddleware, and CSRFMiddleware.

    :param app: The FastAPI application to add middleware to.
    :return: None
    """
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors.allow_origins,
        allow_credentials=settings.cors.allow_credentials,
        allow_methods=settings.cors.allow_methods,
        allow_headers=settings.cors.allow_headers,
        max_age=600,
    )
    app.add_middleware(SentryAsgiMiddleware)
    app.add_middleware(RedisSessionMiddleware)
    app.add_middleware(CSPMiddleware)
    app.add_middleware(CSRFMiddleware)
