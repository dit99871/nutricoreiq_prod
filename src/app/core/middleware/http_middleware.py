import time
import uuid
from typing import List, Union

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

from src.app.core.logger import get_logger
from src.app.core.utils.network import get_client_ip

log = get_logger("http_middleware")


class HTTPMiddleware(BaseHTTPMiddleware):
    """
    Middleware для логирования HTTP-запросов, обработки общих исключений
    и коррекции URL при работе за обратным прокси.
    """

    def __init__(
        self,
        app: ASGIApp,
        trusted_proxies: Optional[List[Union[str, int]]] = None,
    ) -> None:
        super().__init__(app)
        self.trusted_proxies = set(trusted_proxies or [])

    def get_scheme_and_host(self, request: Request) -> tuple[str, str]:
        """
        Получает схему и хост с учетом заголовков прокси.
        """

        # проверяем заголовок X-Forwarded-Proto для определения схемы (http/https)
        scheme = request.headers.get("X-Forwarded-Proto", request.url.scheme)

        # проверяем заголовок Host или X-Forwarded-Host
        host = (
            request.headers.get("X-Forwarded-Host", "").split(",")[0].strip()
            or request.headers.get("Host", "")
            or request.url.hostname
            or ""
        )

        return scheme, host

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # получаем request_id из заголовка или генерируем новый
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())

        # получаем схему и хост с учетом прокси
        scheme, host = self.get_scheme_and_host(request)

        # создаем копию урла с исправленной схемой и хостом
        url = request.url.replace(scheme=scheme, netloc=host)

        # логируем начало обработки запроса
        start_time = time.time()
        client_ip = get_client_ip(request, trusted_proxies=list(self.trusted_proxies))
        user_agent = request.headers.get("user-agent", "unknown")

        log.info(
            "Начало обработки запроса",
            extra={
                "request_id": request_id,
                "method": request.method,
                "url": str(url),
                "client_ip": client_ip,
                "user_agent": user_agent,
                "scheme": scheme,
                "path": url.path,
                "query": str(url.query) if url.query else None,
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
                    "url": str(url),
                    "status_code": response.status_code,
                    "process_time_ms": f"{process_time:.2f}",
                    "scheme": scheme,
                    "path": url.path,
                    "query": str(url.query) if url.query else None,
                },
            )

            # добавляем полезные заголовки в ответ
            response.headers["X-Process-Time"] = f"{process_time:.2f}ms"
            response.headers["X-Request-ID"] = request_id

            # отключаем кеширование для API ответов (без статических файлов)
            if not url.path.startswith("/static/"):
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

        except Exception as e:
            process_time = (time.time() - start_time) * 1000
            log.error(
                "Ошибка при обработке запроса",
                exc_info=True,
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "url": str(url),
                    "process_time_ms": f"{process_time:.2f}",
                    "client_ip": client_ip,
                    "user_agent": user_agent,
                    "scheme": scheme,
                    "path": url.path,
                    "query": str(url.query) if url.query else None,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
            )

            # возвращаем 500 ошибку с request_id для упрощения отладки
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error": "Internal Server Error",
                    "request_id": request_id,
                    "details": "An unexpected error occurred",
                },
                headers={"X-Request-ID": request_id},
            )
