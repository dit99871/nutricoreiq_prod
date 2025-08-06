from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from src.app.core.config import settings
from src.app.core.logger import get_logger

log = get_logger("csrf_middleware")


class CSRFMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Пропуск публичных маршрутов
        if request.url.path in [
            f"{settings.api.prefix}{settings.api.v1.prefix}{settings.api.v1.auth}/login",
            f"{settings.api.prefix}{settings.api.v1.prefix}{settings.api.v1.auth}/register",
        ]:
            return await call_next(request)

        if request.method in ["POST", "PUT", "DELETE", "PATCH"]:
            # Проверка Origin/Referer
            origin = request.headers.get("origin") or request.headers.get("referer")
            if origin and not any(
                origin.startswith(allowed) for allowed in settings.cors.allow_origins
            ):
                log.error(
                    "Invalid origin for request: %s",
                    request.url,
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "message": "Invalid origin",
                    },
                )

            # Извлечение CSRF-токена
            csrf_token = request.headers.get("X-CSRF-Token")
            if not csrf_token and request.method == "POST":
                form_data = await request.form()
                csrf_token = form_data.get("_csrf_token")

            redis_session = request.scope.get("redis_session", {})
            if not redis_session or "csrf_token" not in redis_session:
                log.error(
                    "Invalid session for request: %s",
                    request.url,
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "message": "Invalid session",
                    },
                )

            session_csrf_token = redis_session.get("csrf_token")
            if not csrf_token or csrf_token != session_csrf_token:
                log.error(
                    "Invalid CSRF token for request: %s",
                    request.url,
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "message": "Invalid CSRF token",
                    },
                )

        return await call_next(request)
