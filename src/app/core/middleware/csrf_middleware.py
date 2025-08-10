from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from src.app.core.config import settings
from src.app.core.logger import get_logger

log = get_logger("csrf_middleware")


class CSRFMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Пропуск публичных маршрутов
        if request.url.path in [
            f"{settings.router.prefix}{settings.router.v1.prefix}{settings.router.v1.auth}/login",
            f"{settings.router.prefix}{settings.router.v1.prefix}{settings.router.v1.auth}/register",
            f"{settings.router.prefix}{settings.router.v1.prefix}{settings.router.v1.auth}/refresh",
            f"{settings.router.prefix}{settings.router.v1.prefix}{settings.router.v1.security}/csp-report",
        ]:
            return await call_next(request)

        if request.method in ["POST", "PUT", "DELETE", "PATCH"]:
            # Проверка Origin/Referer
            origin = request.headers.get("origin") or request.headers.get("referer")
            if origin and not any(
                origin.startswith(allowed) for allowed in settings.cors.allow_origins
            ):
                log.error(
                    "Invalid origin for request: %s, IP: %s, User-Agent: %s",
                    request.url,
                    request.client.host,
                    request.headers.get("user-agent", "unknown"),
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "message": "Нет доступа. Пожалуйста, убедитесь, что вы обращаетесь с авторизованного домена.",
                    },
                )

            # Извлечение CSRF-токена из cookie
            csrf_token_cookie = request.cookies.get("csrf_token")
            if not csrf_token_cookie:
                log.error(
                    "CSRF token missing in cookie for request: %s, IP: %s, User-Agent: %s",
                    request.url,
                    request.client.host,
                    request.headers.get("user-agent", "unknown"),
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "message": "Нет доступа. Пожалуйста, обновите страницу и попробуйте ещё раз.",
                    },
                )

            # Извлечение CSRF-токена из сессии
            session = request.scope.get("redis_session", {})
            session_csrf_token = session.get("csrf_token")
            if not session_csrf_token:
                log.error(
                    "CSRF token missing in session for request: %s, IP: %s, User-Agent: %s",
                    request.url,
                    request.client.host,
                    request.headers.get("user-agent", "unknown"),
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "message": "Нет доступа. Пожалуйста, обновите страницу и попробуйте ещё раз.",
                    },
                )

            # Извлечение CSRF-токена из заголовка или формы
            csrf_token = request.headers.get("X-CSRF-Token")
            if not csrf_token and request.method == "POST":
                form_data = await request.form()
                csrf_token = form_data.get("_csrf_token")

            # Отладочный лог для проверки токенов
            log.debug(
                "CSRF check: cookie=%s, header/form=%s, session=%s, URL=%s",
                csrf_token_cookie,
                csrf_token,
                session_csrf_token,
                request.url,
            )

            # Проверка совпадения токенов
            if (
                not csrf_token
                or csrf_token != csrf_token_cookie
                or csrf_token != session_csrf_token
            ):
                log.error(
                    "Invalid CSRF token for request: %s, IP: %s, User-Agent: %s",
                    request.url,
                    request.client.host,
                    request.headers.get("user-agent", "unknown"),
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "message": "Нет доступа. Пожалуйста, обновите страницу и попробуйте ещё раз.",
                    },
                )

        return await call_next(request)
