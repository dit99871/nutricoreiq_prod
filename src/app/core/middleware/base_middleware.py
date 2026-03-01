from abc import ABC
from typing import Optional

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

from src.app.core.logger import get_logger
from src.app.core.utils.network import get_client_ip, get_scheme_and_host
from src.app.core.services.middleware_service import tracing_service, exception_service


class BaseMiddleware(BaseHTTPMiddleware, ABC):
    """
    Базовый класс для middleware с общей логикой обработки запросов и ошибок.

    Предоставляет:
    - Единый способ получения IP-адреса и схемы
    - Стандартизированную обработку ошибок
    - Общие утилиты для логирования
    """

    def __init__(
        self,
        app: ASGIApp,
        trusted_proxies: Optional[list[str]] = None,
    ) -> None:
        super().__init__(app)
        self.trusted_proxies = list(trusted_proxies or [])
        self.logger = get_logger(self.__class__.__name__.lower())

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """Основной метод dispatch с общей логикой"""

        # устанавливаем общие атрибуты запроса
        self._setup_request_attributes(request)

        # устанавливаем trace ID для unified tracing
        if not hasattr(request.state, "trace_id"):
            request.state.trace_id = tracing_service.create_trace_id()

        try:
            # логируем вход в мидлвари
            context = tracing_service.get_request_context(request)
            tracing_service.log_middleware_entry(self.__class__.__name__, context)

            # вызываем конкретную реализацию в дочернем классе
            response = await self.handle_request(request, call_next)

            # логируем выход из мидлвари
            tracing_service.log_middleware_exit(self.__class__.__name__, context)
            return response

        except StarletteHTTPException:
            # пробрасываем HTTP исключения для обработки в FastAPI
            raise

        except Exception as e:
            # проверяем, является ли исключение HTTPException от FastAPI
            # если да, пробрасываем его для корректной обработки
            if hasattr(e, "status_code") and hasattr(e, "detail"):
                raise

            # используем стандартизированную обработку исключений
            context = tracing_service.get_request_context(request)
            return exception_service.handle_middleware_exception(
                self.__class__.__name__, request, e, context
            )

    async def handle_request(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """
        Метод для переопределения в дочерних классах.
        Содержит специфичную для конкретного middleware логику.
        """

        return await call_next(request)

    def _setup_request_attributes(self, request: Request) -> None:
        """Устанавливает общие атрибуты в request.state"""

        # получаем IP-адрес клиента
        client_ip = getattr(request.state, "client_ip", None) or get_client_ip(
            request, trusted_proxies=self.trusted_proxies
        )
        request.state.client_ip = client_ip

        # получаем схему и хост
        scheme, host = get_scheme_and_host(
            request, trusted_proxies=self.trusted_proxies
        )
        request.state.scheme = scheme
        request.state.host = host
        request.state.effective_url = request.url.replace(scheme=scheme, netloc=host)

    async def _handle_exception(
        self, request: Request, exception: Exception
    ) -> Response:
        """
        Стандартизированная обработка непредвиденных исключений.

        По умолчанию логирует ошибку и возвращает 503 Service Unavailable.
        Можно переопределить в дочерних классах для кастомной обработки.
        """

        client_ip = getattr(request.state, "client_ip", "unknown")
        effective_url = getattr(request.state, "effective_url", request.url)

        self.logger.error(
            "Непредвиденная ошибка в %s: %s, URL: %s, IP: %s, User-Agent: %s",
            self.__class__.__name__,
            str(exception),
            effective_url,
            client_ip,
            request.headers.get("user-agent", "unknown"),
            exc_info=True,
        )

        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"message": "Сервис временно недоступен. Попробуйте позже."},
        )

    def _should_skip_path(self, request: Request, skip_paths: set[str]) -> bool:
        """Проверяет, нужно ли пропустить обработку для данного пути"""

        path = request.url.path

        return any(path.startswith(skip_path) for skip_path in skip_paths)

    def _get_request_context(self, request: Request) -> dict:
        """Возвращает контекст запроса для логирования"""

        return {
            "client_ip": getattr(request.state, "client_ip", "unknown"),
            "user_agent": request.headers.get("user-agent", "unknown"),
            "scheme": getattr(request.state, "scheme", "http"),
            "url": getattr(request.state, "effective_url", request.url),
            "path": request.url.path,
            "method": request.method,
        }
