from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.exceptions import HTTPException


class UnwrapExceptionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        """
        Dispatches the request to the next middleware, unwrapping wrapped exceptions.

        This middleware catches exceptions, checks the __cause__ chain,
        and re-raises the original exception if it is an HTTPException.

        :param request: The incoming request.
        :type request: Request
        :param call_next: The next middleware to call.
        :type call_next: Callable[[Request], Awaitable[Response]]
        :return: The response from the next middleware.
        :rtype: Awaitable[Response]
        """
        try:
            return await call_next(request)
        except Exception as exc:
            # находим оригинальное исключение
            original_exc = exc
            while hasattr(original_exc, '__cause__') and original_exc.__cause__:
                original_exc = original_exc.__cause__
            if isinstance(original_exc, HTTPException):
                raise original_exc  # райзим найденное хттп-исключение
            raise  # или ре-райзим оригинальное
