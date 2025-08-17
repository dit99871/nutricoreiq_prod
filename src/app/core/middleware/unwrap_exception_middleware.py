from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.exceptions import HTTPException

from src.app.core.logger import get_logger

log = get_logger("unwrap_exception_middleware")


class UnwrapExceptionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        log.debug("Processing request: %s", request.url)
        try:
            response = await call_next(request)
            log.debug("Request processed successfully: %s", request.url)
            return response
        except Exception as exc:
            log.debug("Caught exception: type=%s, message=%s", type(exc).__name__, str(exc))

            # Проверяем chain исключений
            original_exc = exc
            chain_log = []
            while True:
                chain_log.append(f"type={type(original_exc).__name__}, message={str(original_exc)}")
                if isinstance(original_exc, HTTPException):
                    log.debug("Unwrapped to HTTPException: status=%s, detail=%s",
                              original_exc.status_code, original_exc.detail)
                    raise original_exc
                # Проверяем __cause__
                if hasattr(original_exc, '__cause__') and original_exc.__cause__:
                    original_exc = original_exc.__cause__
                    chain_log.append("Following __cause__")
                    continue
                # Проверяем __context__
                if hasattr(original_exc, '__context__') and original_exc.__context__:
                    original_exc = original_exc.__context__
                    chain_log.append("Following __context__")
                    continue
                break

            log.error("No HTTPException found in chain: %s", "; ".join(chain_log))
            raise  # Re-raise исходное исключение