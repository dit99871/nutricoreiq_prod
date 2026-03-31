from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sentry_sdk.integrations.asgi import SentryAsgiMiddleware

from src.app.core.config import settings

from .csp_middleware import CSPMiddleware
from .csrf_protection_middleware import CSRFProtectionMiddleware
from .http_middleware import HTTPMiddleware
from .privacy_consent_middleware import PrivacyConsentMiddleware
from .session_middleware import SessionMiddleware

__all__ = ("setup_middleware",)


def setup_middleware(app: FastAPI) -> None:
    """
    Добавляет middleware в приложение FastAPI.

    Порядок выполнения запроса (outer -> inner):
    - HTTPMiddleware — outermost: логирование и unified tracing
    - CORSMiddleware — обработка CORS и preflight запросов
    - PrivacyConsentMiddleware — проверка согласия на обработку данных
    - SessionMiddleware — управление сессиями
    - CSRFMiddleware — защита от CSRF атак
    - CSPMiddleware — innermost: заголовки Content Security Policy

    Важно: CORSMiddleware расположен снаружи security-middleware, чтобы
    заголовки Access-Control-Allow-Origin присутствовали в любом ответе,
    включая ошибки 4xx от CSRF и PrivacyConsent.

    Важно: SessionMiddleware находится снаружи CSRFMiddleware, чтобы сессия
    создавалась ДО проверки CSRF токенов.

    :param app: Приложение FastAPI, к которому добавляются middleware.
    :return: None
    """

    app.add_middleware(CSPMiddleware)
    app.add_middleware(CSRFProtectionMiddleware)
    app.add_middleware(
        PrivacyConsentMiddleware, trusted_proxies=settings.run.trusted_proxies
    )
    app.add_middleware(SessionMiddleware, trusted_proxies=settings.run.trusted_proxies)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors.allow_origins,
        allow_credentials=settings.cors.allow_credentials,
        allow_methods=settings.cors.allow_methods,
        allow_headers=settings.cors.allow_headers,
        max_age=600,
    )
    if settings.env.env == "prod":
        app.add_middleware(SentryAsgiMiddleware)
    app.add_middleware(HTTPMiddleware, trusted_proxies=settings.run.trusted_proxies)
