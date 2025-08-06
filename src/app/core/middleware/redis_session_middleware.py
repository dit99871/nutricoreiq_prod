import json
from datetime import datetime, timedelta

from fastapi import Request, Response, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware

from src.app.core.logger import get_logger
from src.app.core.redis import redis_client
from src.app.utils.security import generate_redis_session_id, generate_csrf_token

log = get_logger("redis_session_middleware")


class RedisSessionMiddleware(BaseHTTPMiddleware):

    async def dispatch(self, request: Request, call_next) -> Response:
        session_id = (
            request.cookies.get("redis_session_id") or generate_redis_session_id()
        )
        try:
            # Загрузка сессии из Redis
            session_data = await redis_client.get(f"redis_session:{session_id}")
            if session_data:
                session = json.loads(session_data)
            else:
                session = {
                    "redis_session_id": session_id,
                    "created_at": datetime.now().isoformat(),
                }

            # Генерация или обновление CSRF-токена
            csrf_token = await redis_client.get(f"csrf:{session_id}")
            if not csrf_token:
                csrf_token = generate_csrf_token()
                await redis_client.setex(
                    f"csrf:{session_id}", timedelta(seconds=600), csrf_token
                )
            session["csrf_token"] = csrf_token
            request.scope["redis_session"] = session

            response = await call_next(request)

            # Сохранение сессии в Redis
            await redis_client.set(
                f"redis_session:{session_id}",
                json.dumps(session),
                ex=1800,
            )
            # Установка cookie для session_id
            response.set_cookie(
                key="redis_session_id",
                value=session_id,
                httponly=True,
                secure=True,
                samesite="strict",
            )
            # Установка CSRF-токена в cookie для AJAX
            response.set_cookie(
                key="csrf_token",
                value=csrf_token,
                httponly=False,  # Доступно для JavaScript
                secure=True,
                samesite="strict",
            )
            return response

        except Exception as e:
            log.error(
                "Ошибка в выполнении RedisSessionMiddleware",
            )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "message": "Session service unavailable",
                },
            )
