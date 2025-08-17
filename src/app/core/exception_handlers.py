import sentry_sdk
from fastapi import Request, status, FastAPI
from fastapi.responses import ORJSONResponse
from fastapi.exceptions import HTTPException, RequestValidationError

from src.app.core.config import settings
from src.app.core.exceptions import ExpiredTokenException
from src.app.core.logger import get_logger
from src.app.schemas.responses import ErrorResponse, ErrorDetail

__all__ = ("setup_exception_handlers",)

log = get_logger("exc_handlers")


def expired_token_exception_handler(
    request: Request,
    exc: ExpiredTokenException,
):
    """
    Handle an exception of type ExpiredTokenException.

    :param request: The request object.
    :param exc: The exception object.
    :return: An ORJSONResponse object with the error details and headers.
    """
    error_detail = ErrorDetail(
        message=exc.detail,
        details=None,
    )
    error_response = ErrorResponse(status="error", error=error_detail)
    log.error(
        "HTTP-ошибка по адресу %s: сообщение=%s, статус=%s",
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


# def http_exception_handler(
#     request: Request,
#     exc: HTTPException,
# ):
#     """
#     Обработка http-exception, которые могут возникнуть
#     при выполнении запросов к API.
#
#     :param request: Объект Request, содержащий информацию о запросе
#     :param exc: объект HTTPException, содержащий информацию о возникшей ошибке
#     :return: объект ORJSONResponse, содержащий структурированную информацию об ошибке
#     """
#     if isinstance(exc.detail, dict):
#         message = exc.detail.get("message", "Произошла ошибка")
#         details = exc.detail.get("details")
#     else:
#         message = exc.detail or "Произошла ошибка"
#         details = None
#
#     error_detail = ErrorDetail(
#         message=message,
#         details=details,
#     )
#     error_response = ErrorResponse(status="error", error=error_detail)
#     log.error(
#         "HTTP-ошибка по адресу %s: сообщение=%s, статус=%s",
#         request.url,
#         message,
#         exc.status_code,
#     )
#     log.info("Handling HTTPException: type=%s, status=%s", type(exc).__name__, exc.status_code)
#     return ORJSONResponse(
#         status_code=exc.status_code,
#         content=error_response.model_dump(),
#     )


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
    errors = [{"field": err["loc"][-1], "message": err["msg"]} for err in exc.errors()]
    error_response = ErrorResponse(
        status="error",
        error=ErrorDetail(
            message="Некорректные входные данные", details={"fields": errors}
        ),
    )
    log.error("Ошибка валидации по адресу: %s, ошибки: %s", request.url, errors)

    return ORJSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=error_response.model_dump(),
    )


# def generic_exception_handler(
#     request: Request,
#     exc: Exception,
# ):
#     """
#     Обработка необработанных Exception, которые могут возникнуть при выполнении запросов к API.
#
#     :param request: Объект Request, содержащий информацию о запросе
#     :param exc: объект Exception, содержащий информацию об возникшей ошибке
#     :return: объект ORJSONResponse, содержащий структурированную информацию об ошибке
#     """
#     details = {"field": "server", "message": str(exc)} if settings.DEBUG else None
#     error_response = ErrorResponse(
#         status="error",
#         error=ErrorDetail(message="Внутренняя ошибка сервера", details=details),
#     )
#     log.error(
#         "Непредвиденная ошибка по адресу %s: %s", request.url, str(exc), exc_info=True
#     )
#
#     return ORJSONResponse(
#         status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#         content=error_response.model_dump(),
#     )


def universal_exception_handler(request: Request, exc: Exception):
    log.info("Caught in universal handler: type=%s, message=%s", type(exc).__name__, str(exc))

    # Разворачиваем исключение
    original_exc = exc
    chain_log = []
    while True:
        chain_log.append(f"type={type(original_exc).__name__}, message={str(original_exc)}")
        if isinstance(original_exc, HTTPException):
            log.info("Unwrapped to HTTPException: status=%s, detail=%s",
                      original_exc.status_code, original_exc.detail)
            break
        if hasattr(original_exc, '__cause__') and original_exc.__cause__:
            original_exc = original_exc.__cause__
            chain_log.append("Following __cause__")
            continue
        if hasattr(original_exc, '__context__') and original_exc.__context__:
            original_exc = original_exc.__context__
            chain_log.append("Following __context__")
            continue
        break

    if isinstance(original_exc, HTTPException):
        if isinstance(original_exc.detail, dict):
            message = original_exc.detail.get("message", "Произошла ошибка")
            details = original_exc.detail.get("details")
        else:
            message = original_exc.detail or "Произошла ошибка"
            details = None
        error_detail = ErrorDetail(message=message, details=details)
        error_response = ErrorResponse(status="error", error=error_detail)
        log.error(
            "HTTP-ошибка по адресу %s: сообщение=%s, статус=%s",
            request.url,
            message,
            original_exc.status_code,
        )
        sentry_sdk.set_tag("exception_type", type(original_exc).__name__)  # Для анализа в Sentry/Loki
        sentry_sdk.capture_exception(original_exc)  # Явный capture
        return ORJSONResponse(
            status_code=original_exc.status_code,
            content=error_response.model_dump(),
        )

    # Fallback для других исключений
    details = {"field": "server", "message": str(exc)} if settings.DEBUG else None
    error_response = ErrorResponse(
        status="error",
        error=ErrorDetail(message="Внутренняя ошибка сервера", details=details),
    )
    log.error(
        "Непредвиденная ошибка по адресу %s: %s, chain: %s",
        request.url, str(exc), "; ".join(chain_log), exc_info=True
    )
    sentry_sdk.set_tag("exception_type", type(exc).__name__)
    sentry_sdk.capture_exception(exc)  # Явный capture
    return ORJSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response.model_dump(),
    )


def setup_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(Exception, universal_exception_handler)
    app.add_exception_handler(ExpiredTokenException, expired_token_exception_handler)
    # app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    # app.add_exception_handler(Exception, generic_exception_handler)
