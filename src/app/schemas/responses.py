from typing import Any, Literal, Annotated

from pydantic import Field, StringConstraints

from .base import BaseSchema


class SuccessResponse(BaseSchema):
    status: str = "success"
    data: dict
    meta: dict | None = None


class ErrorDetail(BaseSchema):
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
    status: Literal["error"] = "error"
    error: ErrorDetail
