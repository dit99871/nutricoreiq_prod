"""
Мидлвари только для CSRF защиты - разделенная ответственность
"""

from fastapi import Request, Response, status
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import RequestResponseEndpoint
from starlette.types import ASGIApp

from src.app.core.config import settings
from src.app.core.middleware.base_middleware import BaseMiddleware
from src.app.core.logger import get_logger

log = get_logger(__name__)


class CSRFProtectionMiddleware(BaseMiddleware):
    """Мидлвари только для CSRF защиты"""

    # пути, которые не требуют CSRF защиты
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
            return await call_next(request)

        # для путей ботов возвращаем 404 без CSRF валидации
        bot_paths = ["/xmlrpc.php", "/wp-login.php", "/wp-admin/", "/.well-known/"]
        if any(request.url.path.startswith(path) for path in bot_paths):
            raise StarletteHTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Not Found",
            )

        if request.method in ["POST", "PUT", "DELETE", "PATCH"]:
            # проверка Origin/Referer
            origin = request.headers.get("origin") or request.headers.get("referer")
            if origin and not any(
                origin.startswith(allowed) for allowed in settings.cors.allow_origins
            ):
                log.warning("Invalid origin for %s", request.url.path)
                raise StarletteHTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Нет доступа. Пожалуйста, убедитесь, что вы обращаетесь с авторизованного домена.",
                )

            # проверка CSRF токена
            session = request.scope.get("redis_session", {})
            if not session:
                log.warning("No session found for CSRF validation")
                raise StarletteHTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Время сессии истекло. Пожалуйста, войдите снова.",
                )

            csrf_token = request.headers.get("X-CSRF-Token")
            if not csrf_token:
                csrf_token = request.cookies.get("csrf_token")

            session_csrf_token = session.get("csrf_token")
            if not csrf_token or csrf_token != session_csrf_token:
                log.warning("CSRF token validation failed")
                raise StarletteHTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Нет доступа. Пожалуйста, обновите страницу и попробуйте ещё раз.",
                )

        return await call_next(request)
