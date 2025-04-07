from fastapi import Request
from fastapi.responses import ORJSONResponse
from fastapi.exceptions import HTTPException


def http_exception_handler(request: Request, exc: HTTPException):
    return ORJSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": (
                    exc.detail.get("code")
                    if isinstance(exc.detail, dict)
                    else "unknown"
                ),
                "message": (
                    exc.detail.get("message")
                    if isinstance(exc.detail, dict)
                    else exc.detail
                ),
                "detail": (
                    exc.detail.get("detail") if isinstance(exc.detail, dict) else None
                ),
            }
        },
    )


def generic_exception_handler(request: Request, exc: Exception):
    return ORJSONResponse(
        status_code=500,
        content={"message": "Internal Server Error", "detail": str(exc)},
    )
