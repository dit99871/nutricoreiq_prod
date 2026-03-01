"""
Улучшенный HTTP middleware с unified tracing и оптимизацией
"""

import time
import uuid
from typing import Optional

from fastapi import Request, Response
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import RequestResponseEndpoint
from starlette.types import ASGIApp

from src.app.core.middleware.base_middleware import BaseMiddleware
from src.app.core.services.middleware_service import tracing_service


class HTTPEnhancedMiddleware(BaseMiddleware):
    """
    Улучшенный middleware для логирования HTTP-запросов с unified tracing
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
        """Основная логика HTTP middleware"""

        # получаем request_id из заголовка или генерируем новый
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id

        # получаем унифицированный контекст
        context = tracing_service.get_request_context(request)

        # логируем начало обработки запроса
        start_time = time.time()
        tracing_service.log_middleware_entry(
            self.__class__.__name__,
            context,
            extra_data={
                "process_start": start_time,
                "request_id": request_id,
            },
        )

        try:
            # продолжаем выполнение запроса
            response = await call_next(request)

            # логируем успешное завершение
            process_time = (time.time() - start_time) * 1000
            tracing_service.log_middleware_exit(
                self.__class__.__name__,
                context,
                extra_data={
                    "status_code": response.status_code,
                    "process_time_ms": f"{process_time:.2f}",
                    "request_id": request_id,
                },
            )

            # добавляем полезные заголовки в ответ
            response.headers["X-Process-Time"] = f"{process_time:.2f}ms"
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Trace-ID"] = context["trace_id"]

            # отключаем кеширование для API ответов (без статических файлов)
            if not context["path"].startswith("/static/"):
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

    async def _handle_exception(
        self, request: Request, exception: Exception
    ) -> Response:
        """
        Переопределенная обработка исключений для HTTP middleware.
        Логирует с временем выполнения и пробрасывает дальше.
        """

        request_id = getattr(request.state, "request_id", "unknown")
        context = tracing_service.get_request_context(request)

        tracing_service.log_middleware_error(
            self.__class__.__name__,
            context,
            exception,
            extra_data={
                "request_id": request_id,
                "error_type": type(exception).__name__,
                "error_message": str(exception),
            },
        )

        # пробрасываем исключение дальше для обработки в exception handlers
        raise
