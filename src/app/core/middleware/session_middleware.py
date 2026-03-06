"""
Мидлвари для управления сессиями - разделенная ответственность
"""

from fastapi import Request, Response
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import RequestResponseEndpoint
from starlette.types import ASGIApp

from src.app.core.config import settings
from src.app.core.middleware.base_middleware import BaseMiddleware
from src.app.core.logger import get_logger
from src.app.core.services.session_service import session_service

log = get_logger("session_middleware")


class SessionMiddleware(BaseMiddleware):
    """Middleware для управления сессиями через Redis"""


    # пути, которые не требуют сессии
    EXEMPT_PATHS = {
        "/static/",
        "/metrics",
        "/security/csp-report",
        "/favicon.ico",
        "/robots.txt",
        "/openapi.json",
        "/docs",
        "/redoc",
    }

    def __init__(
        self,
        app: ASGIApp,
        trusted_proxies: list[str] | None = None,
    ) -> None:
        super().__init__(app, trusted_proxies)

    async def handle_request(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """Основная логика Session middleware"""

        # пропуск статических ресурсов и сервисов не требующих сессии
        if self._should_skip_path(request, self.EXEMPT_PATHS):
            return await call_next(request)

        # получаем session_id из cookie или создаем новый
        cookie_session_id = request.cookies.get("redis_session_id")
        session_id = (
            cookie_session_id
            or session_service.create_new_session(cookie_session_id or "generated")[
                "redis_session_id"
            ]
        )

        try:
            # получаем сессию с кешированием и circuit breaker
            session = await session_service.get_session(session_id)

            if not session:
                session = session_service.create_new_session(session_id)

            # обеспечиваем наличие CSRF токена
            session_service.ensure_csrf_token(session)

            # сохраняем сессию в request scope
            request.scope["redis_session"] = session

            # вызов следующего обработчика
            response = await call_next(request)

            # сохраняем сессию (только если изменилась)
            await session_service.save_session(session_id, session)

            # устанавливаем cookies
            self._set_session_cookies(response, session_id, session["csrf_token"])
            return response

        except StarletteHTTPException:
            # пробрасываем HTTP исключения для обработки в FastAPI
            raise

        except Exception as e:
            self.log.error(
                "Session middleware error: %s",
                str(e),
                extra={
                    "trace_id": getattr(request.state, "trace_id", "unknown"),
                    "request_id": getattr(request.state, "request_id", "unknown"),
                    "path": request.url.path,
                    "method": request.method,
                },
                exc_info=True,
            )
            raise

    def _set_session_cookies(
        self, response: Response, session_id: str, csrf_token: str
    ) -> None:
        """Устанавливает cookies для сессии и CSRF-токена"""

        secure = settings.env.env == "prod"
        samesite = "strict" if secure else "lax"

        # установка куков для session_id
        response.set_cookie(
            key="redis_session_id",
            value=session_id,
            httponly=True,
            secure=secure,
            samesite=samesite,
            max_age=settings.redis.session_ttl,
        )

        # установка csrf-токена в куки
        response.set_cookie(
            key="csrf_token",
            value=csrf_token,
            httponly=False,  # доступно для js
            secure=secure,
            samesite=samesite,
            max_age=3600,  # токен живёт 1 час
        )
