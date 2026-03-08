"""
HTTP middleware
"""

import time
from typing import Optional

from fastapi import Request, Response
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import RequestResponseEndpoint
from starlette.types import ASGIApp

from src.app.core.logger import get_logger
from src.app.core.middleware.base_middleware import BaseMiddleware
from src.app.core.services.log_context_service import LogContextService

logger = get_logger("http_middleware")


class HTTPMiddleware(BaseMiddleware):
    """
    Middleware для логирования http-запросов
    """

    def __init__(
        self,
        app: ASGIApp,
        trusted_proxies: Optional[list[str]] = None,
    ) -> None:
        super().__init__(app, trusted_proxies)

    async def handle_request(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """Основная логика http middleware"""

        request_id = getattr(request.state, "request_id", "unknown")

        start_time = time.time()
        request.state.process_start = start_time

        try:
            # продолжаем выполнение запроса
            response = await call_next(request)

            process_time = (time.time() - start_time) * 1000
            request.state.process_time_ms = round(process_time, 2)
            request.state.status_code = response.status_code

            # добавляем полезные заголовки в ответ
            response.headers["X-Process-Time"] = f"{process_time:.2f}ms"
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Trace-ID"] = getattr(
                request.state, "trace_id", "unknown"
            )

            # отключаем кеширование для api ответов (без статических файлов)
            if not request.url.path.startswith("/static/"):
                response.headers["Cache-Control"] = (
                    "no-store, no-cache, must-revalidate, max-age=0"
                )
                response.headers["Pragma"] = "no-cache"
                response.headers["Expires"] = "0"
            # для статических файлов применяем более мягкие настройки
            else:
                response.headers["Pragma"] = "no-cache"
                response.headers["Expires"] = "0"

            # логируем завершение запроса
            context = LogContextService.get_safe_context(request)
            logger.info(
                "Request completed: %s",
                LogContextService.format_context_string(context),
            )

            return response

        except (StarletteHTTPException, RequestValidationError):
            # логируем ошибки перед пробросом
            context = LogContextService.get_safe_context(request)
            logger.warning(
                "Request error in HTTPMiddleware: %s",
                LogContextService.format_context_string(context),
            )
            raise
