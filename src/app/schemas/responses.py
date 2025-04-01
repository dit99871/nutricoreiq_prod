from typing import Any

from .base import BaseSchema


class SuccessResponse(BaseSchema):
    status: str = "success"
    data: dict
    meta: dict | None = None


class ErrorDetail(BaseSchema):
    """Детализация ошибки"""
    code: str
    message: str
    details: dict[str, Any] | None = None


class ErrorResponse(BaseSchema):
    status: str = "error"
    error: ErrorDetail
