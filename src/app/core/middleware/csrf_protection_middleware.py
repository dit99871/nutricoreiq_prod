"""
Мидлвари только для CSRF защиты - разделенная ответственность
"""

import hmac

from fastapi import Request, Response
from starlette.middleware.base import RequestResponseEndpoint
from starlette.types import ASGIApp

from src.app.core.config import settings
from src.app.core.exceptions import (
    CSRFDomainError,
    CSRFSessionExpiredError,
    CSRFTokenError,
)
from src.app.core.logger import get_logger
from src.app.core.middleware.base_middleware import BaseMiddleware
from src.app.core.services.log_context_service import LogContextService

log = get_logger("csrf_middleware")


class CSRFProtectionMiddleware(BaseMiddleware):
    """Мидлвари только для CSRF защиты"""

    # пути, которые не требуют csrf защиты
    EXEMPT_PATHS = [
        f"{settings.router.auth}/login",
        f"{settings.router.auth}/register",
        f"{settings.router.auth}/refresh",
        f"{settings.router.security}/csp-report",
        f"{settings.router.product}/pending",
        "/apis/features.grafana.app/v0alpha1/namespaces/default/ofrep/v1/evaluate/flags",
        "/webhook-test/import",
    ]

    def __init__(
        self,
        app: ASGIApp,
        trusted_proxies: list[str] | None = None,
    ) -> None:
        super().__init__(app, trusted_proxies)

    async def handle_request(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """Основная логика CSRF middleware"""

        # пропуск публичных маршрутов
        if self._should_skip_path(
            request, set(self.EXEMPT_PATHS)
        ) or request.url.path.endswith("/login"):
            try:
                return await call_next(request)
            except Exception:
                raise

        if request.method in ["POST", "PUT", "DELETE", "PATCH"]:
            # проверка Origin/Referer
            origin = request.headers.get("origin") or request.headers.get("referer")
            if origin:
                # нормализация origin - удаление завершающего слэша и параметров
                origin = origin.rstrip("/").split("?")[0]

                if not any(
                    origin == allowed or origin.startswith(allowed + "/")
                    for allowed in settings.cors.allow_origins
                ):
                    context = LogContextService.get_safe_context(request)
                    log.warning(
                        "Не валидный origin: %s | allowed: %s | %s | %s",
                        origin,
                        settings.cors.allow_origins,
                        LogContextService.format_request_line(request),
                        LogContextService.format_context_string(context),
                    )
                    raise CSRFDomainError()

            # проверка csrf токена
            session = request.scope.get("redis_session", {})
            if not session:
                context = LogContextService.get_safe_context(request)
                log.warning(
                    "Не найдена redis-сессия для валидации CSRF: %s | %s",
                    LogContextService.format_request_line(request),
                    LogContextService.format_context_string(context),
                )
                raise CSRFSessionExpiredError()

            csrf_token = request.headers.get("X-CSRF-Token")
            if not csrf_token:
                csrf_token = request.cookies.get("csrf_token")

            session_csrf_token = session.get("csrf_token")
            if not csrf_token or not hmac.compare_digest(
                csrf_token, session_csrf_token
            ):
                context = LogContextService.get_safe_context(request)
                log.warning(
                    "Не найден csrf-токен. %s | %s",
                    LogContextService.format_request_line(request),
                    LogContextService.format_context_string(context),
                )
                raise CSRFTokenError()

        try:
            return await call_next(request)
        except Exception:
            raise
