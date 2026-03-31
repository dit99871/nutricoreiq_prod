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
from src.app.core.repo.privacy_consent import has_user_consent
from src.app.core.services.cache import ConsentCacheService
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

        if self._should_skip_path(request, self.EXEMPT_PATHS):
            return await call_next(request)

        user = getattr(request.state, "user", None)

        if user:
            # авторизованный — проверяем Redis-кеш, при промахе идём в БД
            has_consent = await ConsentCacheService.get(user.id)

            if has_consent is None:
                async for session in db_helper.session_getter():
                    has_consent = await has_user_consent(session, user.id)
                await ConsentCacheService.set(user.id, has_consent)
        else:
            # анонимный — флаг живёт прямо в сессии, которую уже загрузил SessionMiddleware
            redis_session = request.scope.get("redis_session", {})
            has_consent = redis_session.get("privacy_consent", False)

            if not has_consent:
                # первый раз — проверяем cookie/заголовок и сохраняем в сессию
                has_consent = self._check_consent_from_request(request)
                if has_consent:
                    redis_session["privacy_consent"] = True

        if not has_consent:
            raise LegalRestrictionError()

        return await call_next(request)

    def _check_consent_from_request(self, request: Request) -> bool:
        """Проверяет согласие из заголовка или cookie"""
        for source in [
            request.headers.get("X-Privacy-Consent"),
            request.cookies.get("privacy_consent"),
        ]:
            if source:
                try:
                    return bool(json.loads(source).get("personal_data", False))
                except json.JSONDecodeError:
                    pass
        return False
