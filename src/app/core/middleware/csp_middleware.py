from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from src.app.core.config import settings
from src.app.utils.security import generate_csp_nonce


class CSPMiddleware(BaseHTTPMiddleware):

    async def dispatch(self, request: Request, call_next) -> Response:
        csp_nonce = generate_csp_nonce()
        request.state.csp_nonce = csp_nonce

        response = await call_next(request)

        response.headers["Content-Security-Policy-Report-Only"] = (
            "default-src 'self'; "
            f"script-src 'self' 'nonce-{csp_nonce}' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
            f"style-src 'self' 'nonce-{csp_nonce}' https://cdn.jsdelivr.net; "
            f"style-src-attr 'nonce-{csp_nonce}'; "
            "font-src 'self' https://fonts.gstatic.com https://cdn.jsdelivr.net; "
            "img-src 'self' data:; "
            f"connect-src 'self'; "
            "frame-src 'none'; "
            "object-src 'none'; "
            "form-action 'self'; "
            "upgrade-insecure-requests;"
            "report-uri /api/v1/security/csp-report;"
        )
        response.headers["Cache-Control"] = (
            "no-store, no-cache, must-revalidate, max-age=0"
        )
        response.headers["Pragma"] = "no-cache"

        return response
