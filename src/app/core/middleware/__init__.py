from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sentry_sdk.integrations.asgi import SentryAsgiMiddleware

from src.app.core.config import settings

from .csp_middleware import CSPMiddleware
from .csrf_middleware import CSRFMiddleware
from .http_middleware import HTTPMiddleware
from .privacy_consent_middleware import PrivacyConsentMiddleware
from .redis_session_middleware import RedisSessionMiddleware

__all__ = ("setup_middleware",)


def setup_middleware(app: FastAPI) -> None:
    """
    Добавляет middleware в приложение FastAPI.

    Middleware включает:
    - CSPMiddleware (innermost: устанавливает CSP nonce для безопасности контента).
    - CSRFMiddleware (обрабатывает защиту от CSRF, зависит от сессии).
    - RedisSessionMiddleware (управляет сессиями на базе Redis и CSRF-токенами).
    - SentryAsgiMiddleware (если в production: для трассировки ошибок и мониторинга).
    - CORSMiddleware (обрабатывает cross-origin запросы рано, чтобы избежать ненужной обработки).
    - HTTPMiddleware (outermost: логирование, обработка ошибок и коррекции прокси).

    :param app: Приложение FastAPI, к которому добавляются middleware.
    :return: None
    """

    app.add_middleware(CSPMiddleware)
    app.add_middleware(CSRFMiddleware)
    app.add_middleware(RedisSessionMiddleware)
    app.add_middleware(PrivacyConsentMiddleware)
    if settings.env.env == "prod":
        app.add_middleware(SentryAsgiMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors.allow_origins,
        allow_credentials=settings.cors.allow_credentials,
        allow_methods=settings.cors.allow_methods,
        allow_headers=settings.cors.allow_headers,
        max_age=600,
    )
    app.add_middleware(HTTPMiddleware, trusted_proxies=settings.run.trusted_proxies)
