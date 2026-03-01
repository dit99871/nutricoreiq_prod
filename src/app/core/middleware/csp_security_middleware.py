"""
Мидлвари только для CSP безопасности - разделенная ответственность
"""

from fastapi import Request, Response
from starlette.middleware.base import RequestResponseEndpoint

from src.app.core.middleware.base_middleware import BaseMiddleware
from src.app.core.services.middleware_service import security_service


class CSPSecurityMiddleware(BaseMiddleware):
    """Мидлвари только для CSP безопасности"""

    async def handle_request(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """Основная логика CSP middleware"""

        # генерируем CSP nonce
        csp_nonce = security_service.generate_csp_nonce()
        request.state.csp_nonce = csp_nonce

        # продолжаем выполнение запроса
        response = await call_next(request)

        # формируем и добавляем CSP политику
        csp_policy = security_service.build_csp_policy(csp_nonce)
        response.headers["Content-Security-Policy-Report-Only"] = csp_policy

        return response
