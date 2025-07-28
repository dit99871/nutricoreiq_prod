from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from src.app.utils.security import generate_csp_nonce


class CSPMiddleware(BaseHTTPMiddleware):

    async def dispatch(self, request: Request, call_next) -> Response:
        csp_nonce = generate_csp_nonce()
        request.state.csp_nonce = csp_nonce

        response = await call_next(request)

        response.headers['Content-Security-Policy'] = (
            f"default-src 'self'; "
            f"script-src 'self' 'nonce-{csp_nonce}' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
            f"style-src 'self' 'nonce-{csp_nonce}' https://cdn.jsdelivr.net; "
            f"style-src-attr 'self'; "
            f"font-src 'self' https://fonts.gstatic.com https://cdn.jsdelivr.net; "
            f"img-src 'self' data:; "
            f"connect-src 'self'; "
            f"frame-src 'none'; "
            f"object-src 'none'; "
            f"form-action 'self'; "
            f"upgrade-insecure-requests;"
        )

        return response
