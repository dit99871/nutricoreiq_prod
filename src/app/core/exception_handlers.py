from fastapi import FastAPI, Request, status
from fastapi.exceptions import HTTPException, RequestValidationError
from fastapi.responses import ORJSONResponse
from slowapi.errors import RateLimitExceeded
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.app.core.config import settings
from src.app.core.logger import get_logger
from src.app.core.exceptions import (
    BaseApplicationError,
    CSRFSessionExpiredError,
    CSRFDomainError,
    CSRFTokenError,
    ValidationError,
    AuthenticationError,
    AuthorizationError,
    NotFoundError,
    ConflictError,
    DatabaseError,
    ExternalServiceError,
    LegalRestrictionError,
    ExpiredTokenException,
)
from src.app.core.services.log_context_service import LogContextService
from src.app.core.schemas.responses import ErrorDetail, ErrorResponse


log = get_logger("exception_handlers")


def _is_bot_request(path: str, user_agent: str) -> tuple[bool, str]:
    """
    Определяет, является ли запрос от бота.

    :param path: Путь запроса
    :param user_agent: User-Agent строка
    :return: (is_bot, bot_type)
    """
    # Расширенный список бот-путей
    bot_paths = [
        "/xmlrpc.php",
        "/wp-login.php",
        "/wp-admin/",
        "/wp-content/",
        "/wp-includes/",
        "/wp-json/",
        "/.well-known/",
        "/robots.txt",
        "/sitemap.xml",
        "/feed/",
        "/rss/",
        "/track/",
        "/ping/",
        "/phpmyadmin/",
        "/admin.php",
        "/administrator/",
        "/config/",
        "/test/",
        "/debug/",
        "/api/",
        "/graphql/",
        "/webhook/",
    ]

    # проверка путей
    for bot_path in bot_paths:
        if path.startswith(bot_path):
            return True, "path_based"

    # проверка User-Agent на известных ботов
    bot_patterns = [
        "bot",
        "crawler",
        "spider",
        "scraper",
        "curl",
        "wget",
        "python-requests",
        "httpie",
        "postman",
        "insomnia",
        "googlebot",
        "bingbot",
        "slurp",
        "duckduckbot",
        "baiduspider",
    ]

    user_agent_lower = user_agent.lower()
    for pattern in bot_patterns:
        if pattern in user_agent_lower:
            return True, "ua_based"

    return False, "human"


def not_found_exception_handler(
    request: Request,
    exc: StarletteHTTPException,
) -> ORJSONResponse:
    """
    Обработчик 404 ошибок с улучшенной детекцией ботов.

    :param request: Входящий HTTP-запрос
    :param exc: Объект StarletteHTTPException
    :return: JSON-ответ с информацией об ошибке
    """

    path = str(request.url.path)
    method = request.method
    user_agent = request.headers.get("user-agent", "unknown")

    # получаем контекст через LogContextService
    context = LogContextService.get_safe_context(request)

    # определяем тип запроса
    is_bot, bot_type = _is_bot_request(path, user_agent)

    # пропускаем логирование для Grafana API путей
    if "features.grafana.app" in path or "apis/" in path:
        # возвращаем стандартный 404 ответ без логирования
        error_response = ErrorResponse(
            status="error",
            error=ErrorDetail(message="Not found", details=None),
        )
        return ORJSONResponse(status_code=404, content=error_response.model_dump())

    if is_bot:
        # для ботов логируем на дебаг уровне
        log.debug(
            "404 для бот-запроса: %s %s | %s | Тип: %s",
            method,
            path,
            LogContextService.format_context_string(context),
            bot_type,
        )

        # для некоторых типов ботов можно возвращать упрощенный ответ
        if bot_type in ["path_based"]:
            error_response = ErrorResponse(
                status="error",
                error=ErrorDetail(message="Not found", details=None),
            )
            return ORJSONResponse(status_code=404, content=error_response.model_dump())
    else:
        # для легитимных запросов логируем на ворнинг уровне
        log.warning(
            "404 ошибка: %s %s | %s | Referrer: %s",
            method,
            path,
            LogContextService.format_context_string(context),
            request.headers.get("referer", "none")[:200],
        )

    # стандартный ответ
    error_detail = ErrorDetail(
        message="Ресурс не найден",
        details={
            "path": path,
            "method": method,
            "timestamp": context.get("request_id", "unknown"),
        },
    )
    error_response = ErrorResponse(status="error", error=error_detail)

    return ORJSONResponse(
        status_code=404,
        content=error_response.model_dump(),
    )


def expired_token_exception_handler(
    request: Request,
    exc: ExpiredTokenException,
) -> ORJSONResponse:
    """
    Обработчик исключения истекшего токена доступа.

    :param request: Входящий HTTP-запрос
    :param exc: Исключение ExpiredTokenException
    :return: JSON-ответ с информацией об ошибке
    """

    error_detail = ErrorDetail(
        message=exc.detail,
        details=None,
    )
    error_response = ErrorResponse(status="error", error=error_detail)

    # получаем контекст через LogContextService
    context = LogContextService.get_safe_context(request)

    log.warning(
        "Ошибка валидации токена: %s | сообщение=%s, статус=%s",
        LogContextService.format_context_string(context),
        exc.detail,
        exc.status_code,
    )

    headers = {
        "X-Error-Type": "authentication_error",
        "Access-Control-Expose-Headers": "X-Error-Type",
    }
    return ORJSONResponse(
        status_code=exc.status_code,
        content=error_response.model_dump(),
        headers=headers,
    )


def http_exception_handler(
    request: Request,
    exc: StarletteHTTPException,
) -> ORJSONResponse:
    """
    Обработка http-exception, которые могут возникнуть
    при выполнении запросов к API.

    :param request: Объект Request, содержащий информацию о запросе
    :param exc: объект HTTPException, содержащий информацию о возникшей ошибке
    :return: объект ORJSONResponse, содержащий структурированную информацию об ошибке
    """

    if isinstance(exc.detail, dict):
        message = exc.detail.get("message", "Произошла ошибка")
        details = exc.detail.get("details")
    else:
        message = exc.detail or "Произошла ошибка"
        details = None

    error_detail = ErrorDetail(
        message=message,
        details=details,
    )
    error_response = ErrorResponse(status="error", error=error_detail)

    # получаем контекст через LogContextService
    context = LogContextService.get_safe_context(request)

    log.error(
        "HTTP-ошибка: %s | сообщение=%s, статус=%s",
        LogContextService.format_context_string(context),
        message,
        exc.status_code,
    )

    return ORJSONResponse(
        status_code=exc.status_code,
        content=error_response.model_dump(),
    )


def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
):
    """
    Обработка ошибок валидации, которые могут возникнуть
    при выполнении запросов к API.

    :param request: Объект Request, содержащий информацию о запросе
    :param exc: объект RequestValidationError, содержащий информацию о возникшей ошибке
    :return: объект ORJSONResponse, содержащий структурированную информацию об ошибке
    """

    errors = []
    for err in exc.errors():
        # извлекаем и очищаем оригинальное сообщение об ошибке
        if err["type"] == "value_error":
            # удаляем префикс "Value error, " если он есть
            message = str(err.get("msg", ""))
            if message.startswith("Value error, "):
                message = message[13:]  # удаляем "Value error, "
        else:
            message = err["msg"]

        errors.append({"field": ".".join(map(str, err["loc"])), "message": message})

    error_response = ErrorResponse(
        status="error",
        error=ErrorDetail(
            message=(
                "Некорректные входные данные"
                if len(errors) > 1
                else errors[0]["message"]
            ),
            details={"fields": errors} if len(errors) > 1 else None,
        ),
    )

    # получаем контекст через LogContextService
    context = LogContextService.get_safe_context(request)

    log.error(
        "Ошибка валидации: %s | ошибки: %s",
        LogContextService.format_context_string(context),
        errors,
    )

    return ORJSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=error_response.model_dump(),
    )


def generic_exception_handler(
    request: Request,
    exc: Exception,
):
    """
    Обработка необработанных Exception, которые могут возникнуть при выполнении запросов к API.

    :param request: Объект Request, содержащий информацию о запросе
    :param exc: объект Exception, содержащий информацию об возникшей ошибке
    :return: объект ORJSONResponse, содержащий структурированную информацию об ошибке
    """

    # используем X-Forwarded-Proto для определения схемы
    scheme = request.headers.get(
        "X-Forwarded-Proto", request.scope.get("scheme", "http")
    )
    request_url = str(request.url).replace(
        f"{request.scope['scheme']}://", f"{scheme}://"
    )

    details = {"field": "server", "message": str(exc)} if settings.DEBUG else None
    error_response = ErrorResponse(
        status="error",
        error=ErrorDetail(message="Внутренняя ошибка сервера", details=details),
    )

    # создаем унифицированный контекст
    context = LogContextService.extract_context_from_request(request)
    context["url"] = request_url  # Добавляем корректный URL

    log.error(
        f"Непредвиденная ошибка по адресу {request_url}: {str(exc)}",
        extra={
            **context,
            "context_string": LogContextService.format_context_string(context),
        },
    )

    return ORJSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response.model_dump(),
    )


def rate_limit_exceeded_handler(
    request: Request,
    exc: RateLimitExceeded,
) -> ORJSONResponse:
    """
    Обработчик превышения лимита запросов.

    :param request: Входящий HTTP-запрос
    :param exc: Исключение RateLimitExceeded
    :return: JSON-ответ с информацией о превышении лимита
    """

    error_detail = ErrorDetail(
        message="Слишком много запросов. Подождите и попробуйте позже.",
        details={"retry_after": exc.detail} if settings.DEBUG else None,
    )
    error_response = ErrorResponse(status="error", error=error_detail)

    # получаем контекст через LogContextService
    context = LogContextService.get_safe_context(request)

    log.warning(
        "Rate limit exceeded: %s | %s",
        LogContextService.format_context_string(context),
        exc.detail,
    )

    return ORJSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content=error_response.model_dump(),
    )


async def application_error_handler(
    request: Request, exc: BaseApplicationError
) -> ORJSONResponse:
    """Обработчик базовых ошибок приложения"""

    context = LogContextService.get_safe_context(request)
    log.error(
        str(exc),
        extra={
            "context_string": LogContextService.format_context_string(context),
        },
    )

    error_response = ErrorResponse(
        status="error",
        error=ErrorDetail(
            message=exc.message,
            details=exc.details or None,
        ),
    )

    return ORJSONResponse(
        status_code=exc.status_code,
        content=error_response.model_dump(),
    )


__all__ = ("setup_exception_handlers", "application_error_handler")


def setup_exception_handlers(app: FastAPI) -> None:
    """
    Настройка обработчиков исключений приложения.

    Обработчики регистрируются в порядке от наиболее специфичных к наиболее общим.
    """

    # обработчик 404 ошибок (должен быть добавлен до HTTPException)
    app.add_exception_handler(404, not_found_exception_handler)

    # кастомные исключения
    app.add_exception_handler(CSRFSessionExpiredError, application_error_handler)
    app.add_exception_handler(CSRFDomainError, application_error_handler)
    app.add_exception_handler(CSRFTokenError, application_error_handler)
    app.add_exception_handler(ValidationError, application_error_handler)
    app.add_exception_handler(AuthenticationError, application_error_handler)
    app.add_exception_handler(AuthorizationError, application_error_handler)
    app.add_exception_handler(NotFoundError, application_error_handler)
    app.add_exception_handler(ConflictError, application_error_handler)
    app.add_exception_handler(DatabaseError, application_error_handler)
    app.add_exception_handler(ExternalServiceError, application_error_handler)
    app.add_exception_handler(LegalRestrictionError, application_error_handler)
    app.add_exception_handler(ExpiredTokenException, expired_token_exception_handler)
    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

    # обработчик базовых ошибок приложения (для других BaseApplicationError)
    app.add_exception_handler(BaseApplicationError, application_error_handler)

    # стандартные http исключения
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)

    # общий обработчик всех необработанных исключений
    app.add_exception_handler(Exception, generic_exception_handler)
