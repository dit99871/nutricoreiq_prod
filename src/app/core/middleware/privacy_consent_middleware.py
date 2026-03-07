"""
Улучшенный мидлвари для проверки согласия на обработку данных с кешированием
"""
import json

from fastapi import HTTPException, Request, Response, status
from starlette.middleware.base import RequestResponseEndpoint
from starlette.types import ASGIApp

from src.app.core import db_helper
from src.app.core.middleware.base_middleware import BaseMiddleware
from src.app.core.logger import get_logger

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
            return await call_next(request)

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
                    log.warning("Privacy consent required")
                    raise HTTPException(
                        status_code=status.HTTP_451_UNAVAILABLE_FOR_LEGAL_REASONS,
                        detail={
                            "message": "Требуется согласие на обработку персональных данных",
                            "code": "privacy_consent_required",
                            "redirect_url": "/privacy",
                        },
                    )

                return await call_next(request)

        except HTTPException:
            # пробрасываем хттп исключения дальше
            raise

        except Exception as e:
            log.error("PrivacyConsent middleware error: %s", str(e), exc_info=True)
            return await call_next(request)
