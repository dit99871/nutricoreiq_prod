import json
from datetime import datetime

from fastapi import Request, Response, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware

from src.app.core.config import settings
from src.app.core.logger import get_logger
from src.app.core.redis import redis_client
from src.app.core.utils.security import generate_redis_session_id, generate_csrf_token

log = get_logger("redis_session_middleware")


class RedisSessionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        session_id = (
            request.cookies.get("redis_session_id") or generate_redis_session_id()
        )
        try:
            session_data = await redis_client.get(f"redis_session:{session_id}")
            original_session = None
            if session_data:
                session = json.loads(session_data)
                original_session = session.copy()  #  копируем для сравнения изменений
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

            # генерация CSRF-токена, если он отсутствует в сессии
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

            # установка куков для session_id
            response.set_cookie(
                key="redis_session_id",
                value=session_id,
                httponly=True,
                secure=True,
                samesite="strict",
            )

            # установка CSRF-токена в куки
            response.set_cookie(
                key="csrf_token",
                value=csrf_token,
                httponly=False,  # доступно для JS
                secure=True,
                samesite="strict",
                max_age=3600,  # токен живёт 1 час
            )

            return response
        except HTTPException as e:
            if e.status_code == status.HTTP_403_FORBIDDEN:
                raise  # пропускаем ошибки CSRF для обработки в CSRFMiddleware
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
