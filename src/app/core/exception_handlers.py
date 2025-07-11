from fastapi import Request, status
from fastapi.responses import ORJSONResponse
from fastapi.exceptions import HTTPException, RequestValidationError
from src.app.schemas.responses import ErrorResponse, ErrorDetail
from src.app.core.logger import get_logger
from src.app.core.config import settings

log = get_logger("exc_handlers")


def http_exception_handler(request: Request, exc: HTTPException):
    """Обрабатывает HTTPException с формированием структурированного ответа об ошибке"""
    if isinstance(exc.detail, dict):
        code = exc.detail.get("code", "unknown")
        message = exc.detail.get("message", "Произошла ошибка")
        details = exc.detail.get("detail")
    else:
        code = "unknown"
        message = exc.detail or "Произошла ошибка"
        details = None

    error_detail = ErrorDetail(
        code=code,
        message=message,
        details=details
    )

    error_response = ErrorResponse(
        status="error",
        error=error_detail
    )

    log.error(
        "HTTP-ошибка по адресу %s: код=%s, сообщение=%s, статус=%s",
        request.url, code, message, exc.status_code
    )

    return ORJSONResponse(
        status_code=exc.status_code,
        content=error_response.model_dump()
    )


def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Обрабатывает RequestValidationError с формированием структурированного ответа об ошибке"""
    errors = [
        {"field": err["loc"][-1], "message": err["msg"]}
        for err in exc.errors()
    ]
    error_response = ErrorResponse(
        status="error",
        error=ErrorDetail(
            code="validation_error",
            message="Некорректные входные данные",
            details={"fields": errors}
        )
    )

    log.error(
        "Ошибка валидации по адресу %s: ошибки=%s",
        request.url, errors
    )

    return ORJSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=error_response.model_dump()
    )


def generic_exception_handler(request: Request, exc: Exception):
    """Обрабатывает непредвиденные ошибки с формированием структурированного ответа"""
    details = (
        {"field": "server", "message": str(exc)}
        if settings.DEBUG
        else None
    )
    error_response = ErrorResponse(
        status="error",
        error=ErrorDetail(
            code="internal_error",
            message="Внутренняя ошибка сервера",
            details=details
        )
    )

    log.error(
        "Непредвиденная ошибка по адресу %s: %s",
        request.url, str(exc),
        exc_info=True
    )

    return ORJSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response.model_dump()
    )
