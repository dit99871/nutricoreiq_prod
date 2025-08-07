import json
from datetime import datetime

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
            # загрузка сессии из редис
            session_data = await redis_client.get(f"redis_session:{session_id}")
            if session_data:
                session = json.loads(session_data)
            else:
                session = {
                    "redis_session_id": session_id,
                    "created_at": datetime.now().isoformat(),
                }
            request.scope["redis_session"] = session

            # генерация csrf-токена, если он отсутствует в сессии
            csrf_token = session.get("csrf_token") or generate_csrf_token()
            session["csrf_token"] = csrf_token

            response = await call_next(request)

            # сохранение сессии в редис
            await redis_client.set(
                f"redis_session:{session_id}",
                json.dumps(session),
                ex=1800,  # сессия живёт 30 минут
            )

            # установка куков для session_id
            response.set_cookie(
                key="redis_session_id",
                value=session_id,
                httponly=True,
                secure=True,
                samesite="strict",
            )

            # установка csrf-токена в куки
            response.set_cookie(
                key="csrf_token",
                value=csrf_token,
                httponly=False,  # доступно для js
                secure=True,
                samesite="strict",
                max_age=3600,  # токен живёт 1 час
            )

            return response
        except HTTPException as e:
            if e.status_code == status.HTTP_403_FORBIDDEN:
                raise  # пропускаем ошибки csrf без преобразования
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
