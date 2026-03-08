"""
Улучшенный мидлвари для проверки согласия на обработку данных с кешированием
"""

import json

from fastapi import Request, Response, HTTPException
from starlette.middleware.base import RequestResponseEndpoint
from starlette.types import ASGIApp

from src.app.core import db_helper
from src.app.core.exceptions import LegalRestrictionError
from src.app.core.logger import get_logger
from src.app.core.middleware.base_middleware import BaseMiddleware
from src.app.core.services.log_context_service import LogContextService

log = get_logger("privacy_middleware")


class PrivacyConsentMiddleware(BaseMiddleware):
    """Middleware для проверки согласия на обработку персональных данных"""

    # пути, которые не требуют проверки согласия
    EXEMPT_PATHS = {
        "/",
        "/privacy",
        "/about",
        "/static/",
        "/metrics",
        "/security/csp-report",
        "/favicon.ico",
        "/robots.txt",
        "/openapi.json",
        "/docs",
        "/redoc",
        "/privacy/consent",
        "/privacy/consent/status",
        "/auth/login",
        "/auth/register",
        "/auth/logout",
        "/auth/refresh",
    }

    def __init__(
        self,
        app: ASGIApp,
        trusted_proxies: list[str] | None = None,
    ) -> None:
        super().__init__(app, trusted_proxies)

    async def handle_request(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response | None:
        """Основная логика PrivacyConsent middleware"""

        # пропускаем исключенные пути
        if self._should_skip_path(request, self.EXEMPT_PATHS):
            try:
                return await call_next(request)
            except Exception:
                raise

        try:
            # добавляем сессию бд в область видимости запроса
            async for session in db_helper.session_getter():
                # получаем пользователя из запроса
                user = getattr(request.state, "user", None)

                if user:
                    from src.app.core.repo.privacy_consent import has_user_consent

                    has_consent = await has_user_consent(session, user.id)
                else:
                    consent_header = request.headers.get("X-Privacy-Consent")
                    has_consent = False
                    if consent_header:
                        try:
                            consent_data = json.loads(consent_header)
                            has_consent = bool(consent_data.get("personal_data", False))
                        except json.JSONDecodeError:
                            has_consent = False

                    if not has_consent:
                        consent_cookie = request.cookies.get("privacy_consent")
                        if consent_cookie:
                            try:
                                consent_data = json.loads(consent_cookie)
                                has_consent = bool(
                                    consent_data.get("personal_data", False)
                                )
                            except json.JSONDecodeError:
                                has_consent = False

                if not has_consent:
                    context = LogContextService.get_safe_context(request)
                    log.warning(
                        "Требуется согласие на обработку персональных данных: %s",
                        LogContextService.format_context_string(context),
                    )
                    raise LegalRestrictionError(
                        "Требуется согласие на обработку персональных данных"
                    )

                try:
                    return await call_next(request)
                except Exception:
                    raise

        except HTTPException:
            # пробрасываем хттп исключения дальше
            raise

        except Exception as e:
            context = LogContextService.get_safe_context(request)
            log.error(
                "Ошибка в PrivacyConsent мидлвари: %s",
                str(e),
                extra={
                    "context_string": LogContextService.format_context_string(context),
                },
                exc_info=True,
            )
            return await call_next(request)
