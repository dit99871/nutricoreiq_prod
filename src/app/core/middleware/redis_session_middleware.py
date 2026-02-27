import json
from datetime import datetime

import anyio
from fastapi import HTTPException, Request, Response, status
from redis.asyncio import RedisError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import RequestResponseEndpoint
from starlette.requests import ClientDisconnect
from starlette.types import ASGIApp

from src.app.core.config import settings
from src.app.core.middleware.base_middleware import BaseMiddleware
from src.app.core.redis import redis_client
from src.app.core.utils.security import generate_csrf_token, generate_redis_session_id


class RedisSessionMiddleware(BaseMiddleware):
    """Middleware для обработки Redis сессий и CSRF-токенов"""

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
        """Основная логика Redis session middleware"""

        # пропуск статических ресурсов и сервисов не требующих сессии
        if self._should_skip_path(request, self.EXEMPT_PATHS):
            return await call_next(request)

        session_id = (
            request.cookies.get("redis_session_id") or generate_redis_session_id()
        )

        try:
            session_data = await redis_client.get(f"redis_session:{session_id}")
            original_session = None

            if session_data:
                session = json.loads(session_data)
                original_session = session.copy()  # копируем для сравнения изменений
                # продление сессии при активности
                await redis_client.expire(
                    f"redis_session:{session_id}", settings.redis.session_ttl
                )
            else:
                session = {
                    "redis_session_id": session_id,
                    "created_at": datetime.now().isoformat(),
                }

            request.scope["redis_session"] = session

            # генерация csrf-токена, если он отсутствует в сессии
            csrf_token = session.get("csrf_token") or generate_csrf_token()
            session["csrf_token"] = csrf_token

            # вызов следующего обработчика
            response = await call_next(request)

            # сохранение сессии в редис только если она изменилась или новая
            if original_session is None or session != original_session:
                await redis_client.set(
                    f"redis_session:{session_id}",
                    json.dumps(session),
                    ex=settings.redis.session_ttl,
                )

            # установка cookies
            self._set_session_cookies(response, session_id, csrf_token)
            return response

        except HTTPException as e:
            if e.status_code == status.HTTP_403_FORBIDDEN:
                raise  # пробрасываем ошибки csrf для обработки в CSRFMiddleware
            # для других HTTP исключений используем стандартную обработку
            return await self._handle_exception(request, e)

        except StarletteHTTPException as e:
            if e.status_code == status.HTTP_404_NOT_FOUND:
                raise  # 404 ошибки пробрасываем без обработки
            # для других Starlette HTTP исключений используем стандартную обработку
            return await self._handle_exception(request, e)

        except RedisError as e:
            # redis ошибки обрабатываем стандартно
            return await self._handle_exception(request, e)

        except (anyio.EndOfStream, ClientDisconnect):
            # клиент прервал соединение
            context = self._get_request_context(request)
            self.logger.warning(
                "Клиент прервал соединение: %s, IP: %s, User-Agent: %s",
                context["url"],
                context["client_ip"],
                context["user_agent"],
            )
            # создаем специальный Response для отключившегося клиента
            from fastapi import Response

            return Response(status_code=499)

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
