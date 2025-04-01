from .base import BaseSchema


class SuccessResponse(BaseSchema):
    status: str = "success"
    data: dict
    meta: dict | None = None


class ErrorResponse(BaseSchema):
    status: str = "error"
    error: dict
