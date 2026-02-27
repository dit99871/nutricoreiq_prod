from fastapi import Request, Response, status
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import RequestResponseEndpoint
from starlette.types import ASGIApp

from src.app.core.config import settings
from src.app.core.middleware.base_middleware import BaseMiddleware


class CSRFMiddleware(BaseMiddleware):
    """Middleware для защиты от CSRF-атак"""

    # пути, которые не требуют CSRF защиты
    EXEMPT_PATHS = [
        f"{settings.router.auth}/login",
        f"{settings.router.auth}/register",
        f"{settings.router.auth}/refresh",
        f"{settings.router.security}/csp-report",
        f"{settings.router.product}/pending",
        "/apis/features.grafana.app/v0alpha1/namespaces/default/ofrep/v1/evaluate/flags",
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

        context = self._get_request_context(request)

        # пропуск публичных маршрутов
        if self._should_skip_path(
            request, set(self.EXEMPT_PATHS)
        ) or request.url.path.endswith("/login"):
            return await call_next(request)

        if request.method in ["POST", "PUT", "DELETE", "PATCH"]:
            # проверка Origin/Referer
            origin = request.headers.get("origin") or request.headers.get("referer")
            if origin and not any(
                origin.startswith(allowed) for allowed in settings.cors.allow_origins
            ):
                self.logger.error(
                    "Неверный origin для запроса: %s, IP: %s, User-Agent: %s",
                    context["url"],
                    context["client_ip"],
                    context["user_agent"],
                )
                raise StarletteHTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Нет доступа. Пожалуйста, убедитесь, что вы обращаетесь с авторизованного домена.",
                )

            csrf_token_cookie = request.cookies.get("csrf_token")
            if not csrf_token_cookie:
                self.logger.error(
                    "CSRF-токен отсутствует в cookie для запроса: %s, IP: %s, User-Agent: %s",
                    context["url"],
                    context["client_ip"],
                    context["user_agent"],
                )
                raise StarletteHTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Нет доступа. Пожалуйста, обновите страницу и попробуйте ещё раз.",
                )

            session = request.scope.get("redis_session", {})
            if session is None:
                self.logger.error("Сессия не найдена для запроса: %s", context["url"])
                raise StarletteHTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Время сессии истекло. Пожалуйста, войдите снова.",
                )

            session_csrf_token = session.get("csrf_token")
            if not session_csrf_token:
                self.logger.error(
                    "CSRF токен отсутствует в сессии для запроса: %s, IP: %s, User-Agent: %s",
                    context["url"],
                    context["client_ip"],
                    context["user_agent"],
                )
                raise StarletteHTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Нет доступа. Пожалуйста, обновите страницу и попробуйте ещё раз.",
                )

            # извлечение csrf-токена из заголовка или формы
            csrf_token = request.headers.get("X-CSRF-Token")
            if not csrf_token and request.method == "POST":
                form_data = await request.form()
                csrf_token = form_data.get("_csrf_token")

            self.logger.info(
                "Проверка CSRF: cookie=%s, header/form=%s, session=%s, URL=%s",
                csrf_token_cookie,
                csrf_token,
                session_csrf_token,
                context["url"],
            )

            # проверка совпадения токенов
            if (
                not csrf_token
                or csrf_token != csrf_token_cookie
                or csrf_token != session_csrf_token
            ):
                self.logger.error(
                    "Неверный CSRF-токен для запроса: %s, IP: %s, User-Agent: %s",
                    context["url"],
                    context["client_ip"],
                    context["user_agent"],
                )
                raise StarletteHTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Нет доступа. Пожалуйста, обновите страницу и попробуйте ещё раз.",
                )

        return await call_next(request)
