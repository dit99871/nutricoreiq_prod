from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware

from src.app.core.logger import get_logger

log = get_logger("csrf_middleware")


class CSRFMiddleware(BaseHTTPMiddleware):
    """
    Middleware для проверки CSRF-токена
    """

    async def dispatch(self, request: Request, call_next):
        if request.url.path in ["/api/v1/auth/login", "/api/v1/auth/register"]:
            return await call_next(request)

        if request.method in ["POST", "PUT", "DELETE", "PATCH"]:
            csrf_token = request.headers.get("X-CSRF-Token")
            redis_session = request.scope.get("redis_session", {})
            session_csrf_token = redis_session.get("csrf_token")

            if not csrf_token or csrf_token != session_csrf_token:
                log.error(
                    "Неверный CSRF-токен. Запрос: %s",
                    request.url,
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "message": "Неверный CSRF-токен",
                    },
                )
        response = await call_next(request)

        return response
