import json
from datetime import datetime

import anyio
from fastapi import HTTPException, Request, Response, status
from redis.asyncio import RedisError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import ClientDisconnect

from src.app.core.config import settings
from src.app.core.logger import get_logger
from src.app.core.redis import redis_client
from src.app.core.utils.network import get_client_ip
from src.app.core.utils.security import generate_csrf_token, generate_redis_session_id

log = get_logger("redis_session_middleware")


class RedisSessionMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app,
        trusted_proxies: list[str] | None = None,
    ) -> None:
        super().__init__(app)
        self.trusted_proxies = list(trusted_proxies or [])

    async def dispatch(self, request: Request, call_next) -> Response:
        """
        Middleware для обработки redis сессии.

        Это middleware получает или генерирует ID сессии из cookies и извлекает данные сессии из redis.
        Если данные сессии существуют, продлевает время жизни сессии и сохраняет сессию в области запроса.
        Если данные сессии отсутствуют, создает новую сессию.
        Если данные сессии изменились или это новая сессия, сохраняет сессию в redis.
        CSRF-токен генерируется, если он отсутствует в сессии.
        После обработки запроса сессия сохраняется в redis.
        ID сессии и CSRF-токен устанавливаются в cookies ответа.
        Если в процессе возникает исключение, оно логируется и генерируется HTTP-исключение со статусом 503.

        :param request: Объект текущего запроса.
        :param call_next: Следующее middleware в цепочке.
        :return: Объект ответа.
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
            client_ip = getattr(request.state, "client_ip", None) or get_client_ip(
                request, trusted_proxies=self.trusted_proxies
            )
            log.error(
                "Ошибка в RedisSessionMiddleware: %s, IP: %s, User-Agent: %s",
                str(e),
                client_ip,
                request.headers.get("user-agent", "unknown"),
            )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "message": "Сервис недоступен. Пожалуйста, попробуйте позже.",
                },
            )

        except StarletteHTTPException as e:
            if e.status_code == status.HTTP_404_NOT_FOUND:
                # 404 ошибки пробрасываем без обработки
                raise
            client_ip = getattr(request.state, "client_ip", None) or get_client_ip(
                request, trusted_proxies=self.trusted_proxies
            )
            log.error(
                "Starlette HTTP ошибка в RedisSessionMiddleware: %s, IP: %s, User-Agent: %s",
                str(e),
                client_ip,
                request.headers.get("user-agent", "unknown"),
            )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "message": "Сервис недоступен. Пожалуйста, попробуйте позже.",
                },
            )

        except RedisError as e:
            client_ip = getattr(request.state, "client_ip", None) or get_client_ip(
                request, trusted_proxies=self.trusted_proxies
            )
            log.error(
                "Ошибка в RedisSessionMiddleware: %s, IP: %s, User-Agent: %s",
                str(e),
                client_ip,
                request.headers.get("user-agent", "unknown"),
            )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "message": "Сервис недоступен. Пожалуйста, попробуйте позже.",
                },
            )

        except anyio.EndOfStream:
            # Клиент прервал соединение
            client_ip = getattr(request.state, "client_ip", None) or get_client_ip(
                request, trusted_proxies=self.trusted_proxies
            )
            log.warning(
                "Клиент прервал соединение: %s, IP: %s, User-Agent: %s",
                request.url,
                client_ip,
                request.headers.get("user-agent", "unknown"),
            )
            # Возвращаем 499 - клиент закрыл соединение
            return Response(status_code=499)

        except ClientDisconnect:
            # Клиент отключился - нормальная ситуация
            client_ip = getattr(request.state, "client_ip", None) or get_client_ip(
                request, trusted_proxies=self.trusted_proxies
            )
            log.warning(
                "Клиент отключился: %s, IP: %s, User-Agent: %s",
                request.url,
                client_ip,
                request.headers.get("user-agent", "unknown"),
            )
            return Response(status_code=499)  # Client Closed Request

        except Exception as e:
            # логируем непредвиденные ошибки и возвращаем 500
            log.error(
                "Непредвиденная ошибка в RedisSessionMiddleware: %s, URL: %s, Заголовки: %s, Тип исключения: %s",
                str(e),
                request.url,
                dict(request.headers),
                type(e).__name__,
                exc_info=True,
            )
            # Создаем новое 500 исключение для непредвиденных ошибок
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"message": "Внутренняя ошибка сервера при обработке запроса"},
            )
