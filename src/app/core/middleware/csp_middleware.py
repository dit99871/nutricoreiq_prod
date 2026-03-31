"""
Мидлвари только для CSP безопасности - разделенная ответственность
"""

from fastapi import Request, Response
from starlette.middleware.base import RequestResponseEndpoint

from src.app.core.middleware.base_middleware import BaseMiddleware
from src.app.core.config import settings
from src.app.core.utils.security import generate_csp_nonce


class CSPMiddleware(BaseMiddleware):
    """Мидлвари только для CSP безопасности"""

    async def handle_request(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """Основная логика CSP middleware"""

        # генерируем csp nonce
        csp_nonce = generate_csp_nonce()
        request.state.csp_nonce = csp_nonce

        csp_policy = (
            "default-src 'self'; "
            f"script-src 'self' 'nonce-{csp_nonce}' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
            f"style-src 'self' 'nonce-{csp_nonce}' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
            f"style-src-attr 'nonce-{csp_nonce}'; "
            "font-src 'self' https://fonts.gstatic.com https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
            "img-src 'self' data: https:; "
            "connect-src 'self'; "
            "frame-src 'none'; "
            "object-src 'none'; "
            "form-action 'self'; "
            "upgrade-insecure-requests;"
        )

        if settings.env.env == "prod":
            csp_policy += f"report-uri {settings.router.security}/csp-report;"

        # продолжаем выполнение запроса
        response = await call_next(request)

        # формируем и добавляем csp политику
        response.headers["Content-Security-Policy"] = csp_policy

        return response
