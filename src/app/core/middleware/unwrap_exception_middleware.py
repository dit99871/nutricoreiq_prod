from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.exceptions import HTTPException

from src.app.core.logger import get_logger

log = get_logger("unwrap_exception_middleware")


class UnwrapExceptionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        try:
            return await call_next(request)
        except Exception as exc:
            log.debug("Caught exception: %s", type(exc).__name__)

            # Проверяем chain исключений (__cause__ и __context__)
            original_exc = exc
            while True:
                if isinstance(original_exc, HTTPException):
                    log.debug("Unwrapped to HTTPException: status=%s, detail=%s",
                              original_exc.status_code, original_exc.detail,
                    )
                    raise original_exc
                # проверяем __cause__
                if hasattr(original_exc, '__cause__') and original_exc.__cause__:
                    original_exc = original_exc.__cause__
                    log.debug(
                        "Following __cause__: %s",
                        type(original_exc).__name__,
                    )
                    continue
                # проверяем __context__
                if hasattr(original_exc, '__context__') and original_exc.__context__:
                    original_exc = original_exc.__context__
                    log.debug(
                        "Following __context__: %s",
                        type(original_exc).__name__,
                    )
                    continue
                # если ничего не нашли, выходим
                break

            log.debug(
                "No HTTPException found, re-raising original: %s",
                type(exc).__name__,
            )
            raise  # ре-райзим исходное исключение, если оно не хттп
