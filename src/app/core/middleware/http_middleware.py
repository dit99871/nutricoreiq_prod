import time
import uuid

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from src.app.core.logger import get_logger

log = get_logger("http_middleware")


class HTTPMiddleware(BaseHTTPMiddleware):
    """
    Middleware для логирования HTTP-запросов и обработки общих исключений.
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # логирование входящего запроса
        start_time = time.time()
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())

        log.info(
            "Начало обработки запроса",
            extra={
                "request_id": request_id,
                "method": request.method,
                "url": str(request.url),
                "client_ip": client_ip,
                "user_agent": user_agent,
            },
        )

        try:
            response = await call_next(request)

            process_time = (time.time() - start_time) * 1000
            log.info(
                "Запрос успешно обработан",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "url": str(request.url),
                    "status_code": response.status_code,
                    "process_time_ms": f"{process_time:.2f}ms",
                },
            )

            # добавляем время выполнения в заголовки ответа
            response.headers["X-Process-Time"] = f"{process_time:.2f}ms"
            response.headers["X-Request-ID"] = request_id

            return response

        except Exception:
            process_time = (time.time() - start_time) * 1000
            log.error(
                "Ошибка при обработке запроса",
                exc_info=True,
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "url": str(request.url),
                    "process_time_ms": f"{process_time:.2f}ms",
                    "client_ip": client_ip,
                    "user_agent": user_agent,
                },
            )

            # пробрасываем исключение дальше, чтобы его обработали соответсвующие обработчики исключений
            raise
