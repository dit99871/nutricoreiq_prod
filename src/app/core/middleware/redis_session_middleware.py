import json
from datetime import datetime

from fastapi import HTTPException, Request, Response, status
from redis.asyncio import RedisError
from starlette.middleware.base import BaseHTTPMiddleware

from src.app.core.config import settings
from src.app.core.logger import get_logger
from src.app.core.redis import redis_client
from src.app.core.utils.security import (generate_csrf_token,
                                         generate_redis_session_id)

log = get_logger("redis_session_middleware")


class RedisSessionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        """
        Middleware for handling redis session.

        This middleware gets or generates session id from cookies and retrieves session data from redis.
        If session data exists, it extends session expiration time and stores the session in request scope.
        If session data doesn't exist, it creates a new session.
        If session data has changed or it's a new session, it saves the session in redis.
        CSRF token is generated if it's not present in the session.
        After processing of the request, the session is saved in redis.
        Session id and CSRF token are set in response cookies.
        If an exception occurs during the process, it is logged and an HTTP exception with a 503 status code is raised.

        :param request: The current request object.
        :param call_next: The next middleware in the chain.
        :return: The response object.
        """

        # пропуск статических ресурсов и сервисов не требующих сессии
        path = request.url.path
        if path.startswith("/static/") or path in {
            "/metrics",
            "/security/csp-report",
            "/favicon.ico",
            "/robots.txt",
            "/openapi.json",
            "/docs",
            "/redoc",
        }:
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

            return response
        except HTTPException as e:
            if e.status_code == status.HTTP_403_FORBIDDEN:
                raise  # пропускаем ошибки csrf для обработки в CSRFMiddleware
            log.error(
                "Ошибка в RedisSessionMiddleware: %s, IP: %s, User-Agent: %s",
                str(e),
                request.client.host,
                request.headers.get("user-agent", "unknown"),
            )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "message": "Сервис недоступен. Пожалуйста, попробуйте позже.",
                },
            )
        except RedisError as e:
            log.error(
                "Ошибка в RedisSessionMiddleware: %s, IP: %s, User-Agent: %s",
                str(e),
                request.client.host,
                request.headers.get("user-agent", "unknown"),
            )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "message": "Сервис недоступен. Пожалуйста, попробуйте позже.",
                },
            )
        except Exception as e:
            # логируем непредвиденные ошибки и возвращаем 500
            log.error(
                "Непредвиденная ошибка в CSRF middleware: %s, URL: %s, Заголовки: %s",
                str(e),
                request.url,
                dict(request.headers),
                exc_info=True,
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"message": "Внутренняя ошибка сервера при обработке запроса"},
            )
