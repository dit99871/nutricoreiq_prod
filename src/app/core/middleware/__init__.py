from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sentry_sdk.integrations.asgi import SentryAsgiMiddleware

from src.app.core.config import settings

from .csp_security_middleware import CSPSecurityMiddleware
from .csrf_protection_middleware import CSRFProtectionMiddleware
from .http_enhanced_middleware import HTTPEnhancedMiddleware
from .privacy_consent_middleware import PrivacyConsentV2Middleware
from .session_middleware import SessionMiddleware

__all__ = ("setup_middleware",)


def setup_middleware(app: FastAPI) -> None:
    """
    Добавляет улучшенные middleware в приложение FastAPI.

    Корректный порядок (inner -> outer):
    - CORSMiddleware - innermost: обработка preflight запросов
    - CSPSecurityMiddleware - CSP безопасность
    - CSRFProtectionMiddleware - CSRF защита
    - SessionMiddleware - управление сессиями
    - PrivacyConsentV2Middleware - проверка согласия с кешированием
    - SentryAsgiMiddleware - если в production: мониторинг
    - HTTPEnhancedMiddleware - outermost: логирование с unified tracing

    :param app: Приложение FastAPI, к которому добавляются middleware.
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
    app.add_middleware(CSPSecurityMiddleware)
    app.add_middleware(CSRFProtectionMiddleware)
    app.add_middleware(SessionMiddleware, trusted_proxies=settings.run.trusted_proxies)
    app.add_middleware(
        PrivacyConsentV2Middleware, trusted_proxies=settings.run.trusted_proxies
    )
    if settings.env.env == "prod":
        app.add_middleware(SentryAsgiMiddleware)
    app.add_middleware(
        HTTPEnhancedMiddleware, trusted_proxies=settings.run.trusted_proxies
    )
