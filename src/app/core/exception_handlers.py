from fastapi import FastAPI, Request, status
from fastapi.exceptions import HTTPException, RequestValidationError
from fastapi.responses import ORJSONResponse
from slowapi.errors import RateLimitExceeded
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.app.core.config import settings
from src.app.core.exceptions import ExpiredTokenException
from src.app.core.logger import get_logger
from src.app.core.schemas.responses import ErrorDetail, ErrorResponse

__all__ = ("setup_exception_handlers",)

log = get_logger("exc_handlers")


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
    log.warning(
        "Ошибка валидации токена по адресу %s: сообщение=%s, статус=%s",
        request.url,
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
    log.error(
        "HTTP-ошибка по адресу %s: сообщение=%s, статус=%s",
        request.url,
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
    log.error("Ошибка валидации по адресу: %s, ошибки: %s", request.url, errors)

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
    log.error(
        "Непредвиденная ошибка по адресу %s: %s", request_url, str(exc), exc_info=True
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
    log.warning(
        "Rate limit exceeded по адресу %s: %s",
        request.url,
        exc.detail,
    )
    return ORJSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content=error_response.model_dump(),
    )


def setup_exception_handlers(app: FastAPI) -> None:
    """
    Настройка обработчиков исключений приложения.

    Обработчики регистрируются в порядке от наиболее специфичных к наиболее общим.
    """

    # кастомные исключения
    app.add_exception_handler(ExpiredTokenException, expired_token_exception_handler)
    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

    # стандартные http исключения
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)

    # общий обработчик всех необработанных исключений
    app.add_exception_handler(Exception, generic_exception_handler)
