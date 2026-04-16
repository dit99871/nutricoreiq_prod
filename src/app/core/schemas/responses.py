"""Схемы для работы с ответами."""

from typing import Annotated, Any, Literal

from pydantic import Field, StringConstraints

from .base import BaseSchema


class SuccessResponse(BaseSchema):
    """Схема успешного ответа."""

    status: str = "success"
    data: dict
    meta: dict | None = None


class ErrorDetail(BaseSchema):
    """Схема для вывода деталей об ошибке."""

    message: Annotated[str, StringConstraints(to_upper=True, max_length=255)]
    details: Annotated[
        dict[str, Any] | None,
        Field(
            examples=[
                {
                    "field": "email",
                    "message": "Invalid email format",
                },
            ],
        ),
    ] = None


class ErrorResponse(BaseSchema):
    """Схема ответа с ошибкой."""

    status: Literal["error"] = "error"
    error: ErrorDetail
