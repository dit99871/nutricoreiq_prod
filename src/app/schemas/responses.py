from typing import Any, Literal
from pydantic import Field, constr

from .base import BaseSchema


class SuccessResponse(BaseSchema):
    status: str = "success"
    data: dict
    meta: dict | None = None


class ErrorDetail(BaseSchema):
    message: constr(max_length=255)
    details: dict[str, Any] | None = Field(
        default=None, examples=[{"field": "email", "message": "Invalid email format"}]
    )


class ErrorResponse(BaseSchema):
    status: Literal["error"] = "error"
    error: ErrorDetail
