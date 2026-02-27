import time
import uuid
from typing import Optional

from fastapi import Request, Response
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import RequestResponseEndpoint
from starlette.types import ASGIApp

from src.app.core.middleware.base_middleware import BaseMiddleware


class HTTPMiddleware(BaseMiddleware):
    """
    Middleware для логирования HTTP-запросов, обработки общих исключений
    и коррекции URL при работе за обратным прокси.
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

        # логируем начало обработки запроса
        start_time = time.time()
        context = self._get_request_context(request)

        self.logger.info(
            "Начало обработки запроса",
            extra={
                "request_id": request_id,
                "method": context["method"],
                "url": str(context["url"]),
                "client_ip": context["client_ip"],
                "user_agent": context["user_agent"],
                "scheme": context["scheme"],
                "path": context["path"],
                "query": str(context["url"].query) if context["url"].query else None,
            },
        )

        try:
            # продолжаем выполнение запроса
            response = await call_next(request)

            # логируем успешное завершение
            process_time = (time.time() - start_time) * 1000
            self.logger.info(
                "Запрос успешно обработан",
                extra={
                    "request_id": request_id,
                    "method": context["method"],
                    "url": str(context["url"]),
                    "status_code": response.status_code,
                    "process_time_ms": f"{process_time:.2f}",
                    "scheme": context["scheme"],
                    "path": context["path"],
                    "query": (
                        str(context["url"].query) if context["url"].query else None
                    ),
                },
            )

            # добавляем полезные заголовки в ответ
            response.headers["X-Process-Time"] = f"{process_time:.2f}ms"
            response.headers["X-Request-ID"] = request_id

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
        context = self._get_request_context(request)

        self.logger.error(
            "Ошибка при обработке запроса",
            exc_info=True,
            extra={
                "request_id": request_id,
                "method": context["method"],
                "url": str(context["url"]),
                "client_ip": context["client_ip"],
                "user_agent": context["user_agent"],
                "scheme": context["scheme"],
                "path": context["path"],
                "query": str(context["url"].query) if context["url"].query else None,
                "error_type": type(exception).__name__,
                "error_message": str(exception),
            },
        )

        # пробрасываем исключение дальше для обработки в exception handlers
        raise
