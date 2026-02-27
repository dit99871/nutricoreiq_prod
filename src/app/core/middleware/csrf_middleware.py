from fastapi import Request, Response, status
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware

from src.app.core.config import settings
from src.app.core.logger import get_logger
from src.app.core.utils.network import get_client_ip

log = get_logger("csrf_middleware")


class CSRFMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app,
        trusted_proxies: list[str] | None = None,
    ) -> None:
        super().__init__(app)
        self.trusted_proxies = list(trusted_proxies or [])

    async def dispatch(self, request: Request, call_next) -> Response:
        # получаем реальный IP клиента
        client_ip = getattr(request.state, "client_ip", None) or get_client_ip(
            request, trusted_proxies=self.trusted_proxies
        )

        scheme = getattr(request.state, "scheme", None) or request.scope.get(
            "scheme", "http"
        )
        request_url = str(request.url).replace(
            f"{request.scope['scheme']}://", f"{scheme}://"
        )

        # пропуск публичных маршрутов
        if request.url.path in [
            f"{settings.router.auth}/login",
            f"{settings.router.auth}/register",
            f"{settings.router.auth}/refresh",
            f"{settings.router.security}/csp-report",
            f"{settings.router.product}/pending",
            "/apis/features.grafana.app/v0alpha1/namespaces/default/ofrep/v1/evaluate/flags",
        ] or request.url.path.endswith("/login"):
            return await call_next(request)

        if request.method in ["POST", "PUT", "DELETE", "PATCH"]:
            # проверка Origin/Referer
            origin = request.headers.get("origin") or request.headers.get("referer")
            if origin and not any(
                origin.startswith(allowed) for allowed in settings.cors.allow_origins
            ):
                log.error(
                    "Неверный origin для запроса: %s, IP: %s, User-Agent: %s",
                    request_url,
                    client_ip,
                    request.headers.get("user-agent", "unknown"),
                )
                raise StarletteHTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Нет доступа. Пожалуйста, убедитесь, что вы обращаетесь с авторизованного домена.",
                )

            csrf_token_cookie = request.cookies.get("csrf_token")
            if not csrf_token_cookie:
                log.error(
                    "CSRF-токен отсутствует в cookie для запроса: %s, IP: %s, User-Agent: %s",
                    request_url,
                    client_ip,
                    request.headers.get("user-agent", "unknown"),
                )
                raise StarletteHTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Нет доступа. Пожалуйста, обновите страницу и попробуйте ещё раз.",
                )

            session = request.scope.get("redis_session", {})
            if session is None:
                log.error("Сессия не найдена для запроса: %s", request_url)
                raise StarletteHTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Время сессии истекло. Пожалуйста, войдите снова.",
                )

            session_csrf_token = session.get("csrf_token")
            if not session_csrf_token:
                log.error(
                    "CSRF токен отсутствует в сессии для запроса: %s, IP: %s, User-Agent: %s",
                    request_url,
                    client_ip,
                    request.headers.get("user-agent", "unknown"),
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

            log.info(
                "Проверка CSRF: cookie=%s, header/form=%s, session=%s, URL=%s",
                csrf_token_cookie,
                csrf_token,
                session_csrf_token,
                request_url,
            )

            # проверка совпадения токенов
            if (
                not csrf_token
                or csrf_token != csrf_token_cookie
                or csrf_token != session_csrf_token
            ):
                log.error(
                    "Неверный CSRF-токен для запроса: %s, IP: %s, User-Agent: %s",
                    request_url,
                    client_ip,
                    request.headers.get("user-agent", "unknown"),
                )
                raise StarletteHTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Нет доступа. Пожалуйста, обновите страницу и попробуйте ещё раз.",
                )

        return await call_next(request)
