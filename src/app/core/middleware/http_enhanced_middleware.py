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

        start_time = time.time()
        request.state.process_start = start_time

        try:
            # продолжаем выполнение запроса
            response = await call_next(request)

            process_time = (time.time() - start_time) * 1000
            request.state.process_time_ms = round(process_time, 2)

            # добавляем полезные заголовки в ответ
            response.headers["X-Process-Time"] = f"{process_time:.2f}ms"
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Trace-ID"] = getattr(
                request.state, "trace_id", "unknown"
            )

            # отключаем кеширование для API ответов (без статических файлов)
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

            return response

        except (StarletteHTTPException, RequestValidationError):
            raise
