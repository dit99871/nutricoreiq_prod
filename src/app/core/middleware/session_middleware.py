"""
Мидлвари для управления сессиями - разделенная ответственность
"""
import uuid

from fastapi import Request, Response
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import RequestResponseEndpoint
from starlette.types import ASGIApp

from src.app.core.config import settings
from src.app.core.logger import get_logger
from src.app.core.middleware.base_middleware import BaseMiddleware
from src.app.core.services.log_context_service import LogContextService
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
            try:
                return await call_next(request)
            except Exception:
                raise

        # получаем session_id из кук или создаем новый
        cookie_session_id = request.cookies.get("redis_session_id")

        if cookie_session_id:
            session_id = cookie_session_id
        else:
            # создаем новую сессию только если нет cookie
            session_id = str(uuid.uuid4())

        try:
            # получаем сессию с кешированием и circuit breaker
            session = await session_service.get_session(session_id)

            if not session:
                session = session_service.create_new_session(session_id)

            # обеспечиваем наличие csrf токена
            session_service.ensure_csrf_token(session)

            # сохраняем сессию в область видимости запроса
            request.scope["redis_session"] = session

            # вызов следующего обработчика
            response = await call_next(request)

            # сохраняем сессию (только если изменилась) с валидацией
            saved_successfully = await session_service.save_session(session_id, session)

            if not saved_successfully:
                context = LogContextService.get_safe_context(request)
                log.error(
                    "Не удалось сохранить сессию в Redis: %s",
                    LogContextService.format_context_string(context),
                )

            # устанавливаем куки
            self._set_session_cookies(response, session_id, session["csrf_token"])
            return response

        except StarletteHTTPException:
            # пробрасываем хттп исключения для обработки в фастапи
            raise

        except Exception as e:
            context = LogContextService.get_safe_context(request)
            log.error(
                "Ошибка в Session мидлвари: %s",
                str(e),
                extra={
                    "context_string": LogContextService.format_context_string(context),
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
