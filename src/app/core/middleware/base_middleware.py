"""
Базовый middleware для обработки запросов и ошибок.
"""

from abc import ABC

from fastapi import Request, Response
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

from src.app.core import settings
from src.app.core.exceptions import BaseApplicationError
from src.app.core.logger import get_logger
from src.app.core.services.log_context_service import LogContextService

logger = get_logger("base_middleware")


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
        trusted_proxies: list[str] = settings.run.trusted_proxies,
    ) -> None:
        super().__init__(app)
        self.trusted_proxies = list(trusted_proxies or [])

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """Основной метод dispatch с общей логикой"""

        # устанавливаем контекст только один раз
        if not hasattr(request.state, "request_id"):
            LogContextService.setup_request_context(request, self.trusted_proxies)

        try:
            # вызываем конкретную реализацию в дочернем классе
            response = await self.handle_request(request, call_next)
            return response

        except StarletteHTTPException as e:
            # хттп исключения логируем тихо, без полного трейсбека
            context = LogContextService.get_safe_context(request)
            logger.warning(
                "HTTP исключение в %s: %s [status=%s] %s | %s",
                self.__class__.__name__,
                e.detail,
                e.status_code,
                LogContextService.format_request_line(request),
                LogContextService.format_context_string(context),
            )

            # пробрасываем хттп исключения для обработки в фастапи
            raise

        except Exception as e:
            # Проверяем, является ли исключение BaseApplicationError
            if isinstance(e, BaseApplicationError):
                # прямая обработка BaseApplicationError
                from src.app.core.exception_handlers import application_error_handler

                response = await application_error_handler(request, e)
                return response

            context = LogContextService.get_safe_context(request)
            logger.error(
                "Непредвиденная ошибка в %s: %s",
                self.__class__.__name__,
                str(e),
                extra={
                    "context_string": LogContextService.format_context_string(context),
                },
                exc_info=True,
            )
            raise

    async def handle_request(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """
        Метод для переопределения в дочерних классах.
        Содержит специфичную для конкретного middleware логику.
        """

        return await call_next(request)

    @staticmethod
    def _should_skip_path(request: Request, skip_paths: set[str]) -> bool:
        """Проверяет, нужно ли пропустить обработку для данного пути"""

        path = request.url.path
        return any(path.startswith(skip_path) for skip_path in skip_paths)
