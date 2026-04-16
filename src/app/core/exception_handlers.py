"""Обработчики исключений приложения и унифицированные ответы об ошибках."""

from fastapi import FastAPI, Request, status
from fastapi.exceptions import HTTPException, RequestValidationError
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.app.core.config import settings
from src.app.core.exceptions import (
    AuthenticationError,
    AuthorizationError,
    BaseApplicationError,
    ConflictError,
    CSRFDomainError,
    CSRFSessionExpiredError,
    CSRFTokenError,
    DatabaseError,
    ExpiredTokenException,
    ExternalServiceError,
    LegalRestrictionError,
    NotFoundError,
    ValidationError,
)
from src.app.core.logger import get_logger
from src.app.core.schemas.responses import ErrorDetail, ErrorResponse
from src.app.core.services.log_context_service import LogContextService

log = get_logger("exception_handlers")


# легитимные пути, которые могут запрашивать любые боты и люди без вреда
LEGITIMATE_BOT_PATHS = [
    "/.well-known/",  # Let's Encrypt, security.txt, мобильные ассеты
    "/robots.txt",  # Директива для всех краулеров
    "/sitemap.xml",  # Карта сайта для поисковиков
    "/feed/",  # RSS-лента
    "/rss/",  # Альтернативный RSS
    "/track/",  # Пиксели отслеживания email/аналитики
    "/ping/",  # Пингбэки, health checks
    "/api/",  # Публичное API фронтенда/партнёров
    "/graphql/",  # GraphQL эндпоинт
    "/webhook/",  # Внешние интеграции
]

# пути, характерные для сканеров уязвимостей, брутфорса или ошибочных переходов
SUSPICIOUS_PATHS = [
    "/xmlrpc.php",  # WordPress RPC (часто атакуется)
    "/wp-login.php",  # Вход в админку WP
    "/wp-admin/",  # Админ-панель WP
    "/wp-content/",  # Контент WP (может использоваться для определения версий)
    "/wp-includes/",  # Ядро WP (определение версий)
    "/wp-json/",  # REST API WP (иногда легитимно, но часто сканируется)
    "/phpmyadmin/",  # Администрирование БД
    "/admin.php",  # Универсальная админка
    "/administrator/",  # Joomla/другие CMS
    "/config/",  # Конфигурационные файлы
    "/test/",  # Тестовые страницы разработчиков
    "/debug/",  # Отладочные эндпоинты
]


def _is_bot_request(path: str, user_agent: str) -> tuple[bool, str]:
    """
    Определяет, является ли запрос ботом, и возвращает категорию.

    :return: (is_bot, bot_category)
        bot_category может быть:
        - "legitimate_path"   - путь из белого списка (API, robots.txt и т.п.)
        - "suspicious_path"   - путь, типичный для сканеров уязвимостей
        - "ua_based"          - бот определён по User-Agent
        - "human"             - не бот
    """

    # 1. проверка путей (более приоритетна, чем UA)
    for legit_path in LEGITIMATE_BOT_PATHS:
        if path.startswith(legit_path):
            return True, "legitimate_path"

    for susp_path in SUSPICIOUS_PATHS:
        if path.startswith(susp_path):
            return True, "suspicious_path"

    # 2. проверка User-Agent на признаки бота
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
) -> JSONResponse:
    """Обработчик 404 ошибок с разделением по категориям."""

    path = str(request.url.path)
    method = request.method
    user_agent = request.headers.get("user-agent", "unknown")
    context = LogContextService.get_safe_context(request)

    is_bot, bot_category = _is_bot_request(path, user_agent)

    # исключение для внутреннего мониторинга Grafana
    if "features.grafana.app" in path or "apis/" in path:
        error_response = ErrorResponse(
            status="error",
            error=ErrorDetail(message="Not found", details=None),
        )
        return JSONResponse(status_code=404, content=error_response.model_dump())

    # логирование в зависимости от категории
    if is_bot and bot_category == "legitimate_path":
        log.info(
            "404-я, легитимный бот: %s | %s",
            LogContextService.format_request_line(request),
            LogContextService.format_context_string(context),
        )
    else:
        # сканеры, боты с подозрительными UA, люди — все на WARNING
        log.warning(
            "404-я ошибка: %s | %s | Referrer: %s",
            LogContextService.format_request_line(request),
            LogContextService.format_context_string(context),
            request.headers.get("referer", "none")[:200],
        )

    # формируем ответ
    error_detail = ErrorDetail(
        message="Ресурс не найден",
        details={
            "path": path,
            "method": method,
            "timestamp": context.get("request_id", "unknown"),
        },
    )
    error_response = ErrorResponse(status="error", error=error_detail)
    return JSONResponse(status_code=404, content=error_response.model_dump())


def expired_token_exception_handler(
    request: Request,
    exc: ExpiredTokenException,
) -> JSONResponse:
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
        "Ошибка валидации токена: %s | %s",
        LogContextService.format_request_line(request),
        LogContextService.format_context_string(context),
    )

    headers = {
        "X-Error-Type": "authentication_error",
        "Access-Control-Expose-Headers": "X-Error-Type",
    }
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response.model_dump(),
        headers=headers,
    )


def http_exception_handler(
    request: Request,
    exc: StarletteHTTPException,
) -> JSONResponse:
    """
    Обработка http-exception, которые могут возникнуть
    при выполнении запросов к API.

    :param request: Объект Request, содержащий информацию о запросе
    :param exc: объект HTTPException, содержащий информацию о возникшей ошибке
    :return: объект JSONResponse, содержащий структурированную информацию об ошибке
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

    if exc.status_code >= 500:
        log.error(
            "HTTP-ошибка %s: %s | %s",
            exc.status_code,
            LogContextService.format_request_line(request),
            LogContextService.format_context_string(context),
        )
    else:
        log.warning(
            "HTTP-ошибка %s: %s | %s",
            exc.status_code,
            LogContextService.format_request_line(request),
            LogContextService.format_context_string(context),
        )

    return JSONResponse(
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
    :return: объект JSONResponse, содержащий структурированную информацию об ошибке
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
        "Ошибка валидации: %s | %s | ошибки: %s",
        LogContextService.format_request_line(request),
        LogContextService.format_context_string(context),
        errors,
    )

    return JSONResponse(
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
    :return: объект JSONResponse, содержащий структурированную информацию об ошибке
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
        "Непредвиденная ошибка: %s | %s",
        LogContextService.format_request_line(request),
        LogContextService.format_context_string(context),
        extra={
            "context_string": LogContextService.format_context_string(context),
        },
        exc_info=True,
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response.model_dump(),
    )


def rate_limit_exceeded_handler(
    request: Request,
    exc: RateLimitExceeded,
) -> JSONResponse:
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
        "Превышена частота запросов. %s | %s | детали: %s",
        LogContextService.format_request_line(request),
        LogContextService.format_context_string(context),
        exc.detail,
    )

    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content=error_response.model_dump(),
    )


async def application_error_handler(
    request: Request, exc: BaseApplicationError
) -> JSONResponse:
    """
    Обработчик базовых ошибок приложения.

    Разделяет логирование по смыслу исключения:
    - DatabaseError, ExternalServiceError — реальные сбои сервера, уровень ERROR
    - остальные BaseApplicationError (CSRF, Auth, NotFound и др.) — штатные отказы,
      приложение сработало корректно, уровень WARNING

    :param request: Входящий HTTP-запрос
    :param exc: Исключение унаследованное от BaseApplicationError
    :return: JSON-ответ с информацией об ошибке
    """

    context = LogContextService.get_safe_context(request)
    context_str = LogContextService.format_context_string(context)
    request_line = LogContextService.format_request_line(request)

    # реальные ошибки сервера — логируем как error
    server_errors = (DatabaseError, ExternalServiceError)

    if isinstance(exc, server_errors):
        log.error(
            "Ошибка сервера %s: %s | %s",
            exc.status_code,
            request_line,
            context_str,
        )
    else:
        # штатные отказы (csrf, auth, notfound, legalrestriction и т.д.) — warning
        log.warning(
            "Отказ %s: %s | %s",
            exc.status_code,
            request_line,
            context_str,
        )

    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            status="error",
            error=ErrorDetail(
                message=exc.message,
                details=exc.details or None,
            ),
        ).model_dump(),
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
