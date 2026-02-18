import time
import uuid
from typing import Optional

from fastapi import Request, Response
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

from src.app.core.logger import get_logger
from src.app.core.utils.network import get_client_ip, get_scheme_and_host

log = get_logger("http_middleware")


class HTTPMiddleware(BaseHTTPMiddleware):
    """
    Middleware для логирования HTTP-запросов, обработки общих исключений
    и коррекции URL при работе за обратным прокси.
    """

    def __init__(
        self,
        app: ASGIApp,
        trusted_proxies: Optional[list[str]] = None,
    ) -> None:
        super().__init__(app)
        self.trusted_proxies = list(trusted_proxies or [])

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # получаем request_id из заголовка или генерируем новый
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())

        scheme, host = get_scheme_and_host(
            request, trusted_proxies=self.trusted_proxies
        )
        effective_url = request.url.replace(scheme=scheme, netloc=host)

        # логируем начало обработки запроса
        start_time = time.time()
        client_ip = get_client_ip(request, trusted_proxies=self.trusted_proxies)
        user_agent = request.headers.get("user-agent", "unknown")

        log.info(
            "Начало обработки запроса",
            extra={
                "request_id": request_id,
                "method": request.method,
                "url": str(effective_url),
                "client_ip": client_ip,
                "user_agent": user_agent,
                "scheme": scheme,
                "path": effective_url.path,
                "query": str(effective_url.query) if effective_url.query else None,
            },
        )

        try:
            # добавляем request_id в состояние запроса для использования в других частях приложения
            request.state.request_id = request_id

            # продолжаем выполнение запроса
            response = await call_next(request)

            # логируем успешное завершение
            process_time = (time.time() - start_time) * 1000
            log.info(
                "Запрос успешно обработан",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "url": str(effective_url),
                    "status_code": response.status_code,
                    "process_time_ms": f"{process_time:.2f}",
                    "scheme": scheme,
                    "path": effective_url.path,
                    "query": str(effective_url.query) if effective_url.query else None,
                },
            )

            # добавляем полезные заголовки в ответ
            response.headers["X-Process-Time"] = f"{process_time:.2f}ms"
            response.headers["X-Request-ID"] = request_id

            # отключаем кеширование для API ответов (без статических файлов)
            if not effective_url.path.startswith("/static/"):
                response.headers["Cache-Control"] = (
                    "no-store, no-cache, must-revalidate, max-age=0"
                )
                response.headers["Pragma"] = "no-cache"
                response.headers["Expires"] = "0"
            # для статических файлов применяем более мягкие настройки
            else:
                response.headers["Pragma"] = "no-cache"
                response.headers["Expires"] = "0"

            return response

        except (StarletteHTTPException, RequestValidationError):
            raise

        except Exception as e:
            process_time = (time.time() - start_time) * 1000
            log.error(
                "Ошибка при обработке запроса",
                exc_info=True,
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "url": str(effective_url),
                    "process_time_ms": f"{process_time:.2f}",
                    "client_ip": client_ip,
                    "user_agent": user_agent,
                    "scheme": scheme,
                    "path": effective_url.path,
                    "query": str(effective_url.query) if effective_url.query else None,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
            )
            raise
