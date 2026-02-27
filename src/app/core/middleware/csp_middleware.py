from fastapi import Request, Response
from starlette.middleware.base import RequestResponseEndpoint

from src.app.core.config import settings
from src.app.core.middleware.base_middleware import BaseMiddleware
from src.app.core.utils.security import generate_csp_nonce


class CSPMiddleware(BaseMiddleware):
    """Middleware для установки Content Security Policy заголовков"""

    async def handle_request(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """Основная логика CSP middleware"""

        csp_nonce = generate_csp_nonce()
        request.state.csp_nonce = csp_nonce

        response = await call_next(request)

        # формируем CSP политику
        csp_policy = self._build_csp_policy(csp_nonce)

        # добавляем report-uri только в production
        if settings.env.env == "prod":
            csp_policy += f"report-uri {settings.router.security}/csp-report;"

        response.headers["Content-Security-Policy-Report-Only"] = csp_policy

        return response

    def _build_csp_policy(self, csp_nonce: str) -> str:
        """Строит CSP политику с nonce"""

        return (
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
