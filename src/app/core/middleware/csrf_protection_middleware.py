"""
Мидлвари только для CSRF защиты - разделенная ответственность
"""

from fastapi import Request, Response, status
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import RequestResponseEndpoint
from starlette.types import ASGIApp

from src.app.core.config import settings
from src.app.core.middleware.base_middleware import BaseMiddleware
from src.app.core.services.middleware_service import security_service, tracing_service


class CSRFProtectionMiddleware(BaseMiddleware):
    """Мидлвари только для CSRF защиты"""

    # пути, которые не требуют CSRF защиты
    EXEMPT_PATHS = [
        f"{settings.router.auth}/login",
        f"{settings.router.auth}/register",
        f"{settings.router.auth}/refresh",
        f"{settings.router.security}/csp-report",
        f"{settings.router.product}/pending",
        "http://nutricoreiq.ru/apis/features.grafana.app/v0alpha1/namespaces/default/ofrep/v1/evaluate/flags",
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

        context = tracing_service.get_request_context(request)

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
            if not security_service.validate_origin(request):
                tracing_service.log_middleware_error(
                    self.__class__.__name__,
                    context,
                    Exception(f"Invalid origin for {request.url.path}"),
                )
                raise StarletteHTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Нет доступа. Пожалуйста, убедитесь, что вы обращаетесь с авторизованного домена.",
                )

            # проверка CSRF токена
            session = request.scope.get("redis_session", {})
            if not session:
                tracing_service.log_middleware_error(
                    self.__class__.__name__,
                    context,
                    Exception("No session found for CSRF validation"),
                )
                raise StarletteHTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Время сессии истекло. Пожалуйста, войдите снова.",
                )

            if not security_service.validate_csrf_token(request, session):
                tracing_service.log_middleware_error(
                    self.__class__.__name__,
                    context,
                    Exception("CSRF token validation failed"),
                )
                raise StarletteHTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Нет доступа. Пожалуйста, обновите страницу и попробуйте ещё раз.",
                )

        return await call_next(request)
