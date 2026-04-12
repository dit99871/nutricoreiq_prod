"""
Мидлварь для проверки согласия на обработку данных с кешированием
"""

import json
from typing import Any

from fastapi import Request, Response
from starlette.middleware.base import RequestResponseEndpoint
from starlette.types import ASGIApp

from src.app.core import db_helper
from src.app.core.constants import ACCESS_TOKEN_TYPE, TOKEN_TYPE_FIELD
from src.app.core.exceptions import (
    AuthenticationError,
    ExpiredTokenException,
    ExternalServiceError,
    LegalRestrictionError,
    NotFoundError,
)
from src.app.core.logger import get_logger
from src.app.core.middleware.base_middleware import BaseMiddleware
from src.app.core.repo.user import get_user_by_uid
from src.app.core.repo.privacy_consent import has_user_consent
from src.app.core.services.cache import ConsentCacheService
from src.app.core.services.jwt_service import decode_jwt
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
        trusted_proxies: list[str],
    ) -> None:
        super().__init__(app, trusted_proxies)

    async def handle_request(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response | None:

        if self._should_skip_path(request, self.EXEMPT_PATHS):
            return await call_next(request)

        user_id = self._get_user_id_from_token(request)

        if user_id:
            has_consent = await self._check_authorized_consent(user_id)
        else:
            has_consent = self._check_anonymous_consent(request)

        if not has_consent:
            context = LogContextService.get_safe_context(request)
            log.warning(
                "Требуется согласие на обработку персональных данных: %s | %s",
                LogContextService.format_request_line(request),
                LogContextService.format_context_string(context),
            )
            raise LegalRestrictionError()

        return await call_next(request)

    def _get_user_id_from_token(self, request: Request) -> str | None:
        """Возвращает uid (str) из access-токена"""

        access_token = request.cookies.get(ACCESS_TOKEN_TYPE)
        if not access_token:
            return None

        try:
            payload: dict[str, Any] | None = decode_jwt(access_token)
            if not payload:
                return None
            if payload.get(TOKEN_TYPE_FIELD) != ACCESS_TOKEN_TYPE:
                return None
            return payload.get("sub")  # uid: str

        except (ExpiredTokenException, AuthenticationError, ExternalServiceError):
            return None

    async def _check_authorized_consent(self, uid: str) -> bool:
        try:
            async for session in db_helper.session_getter():
                user = await get_user_by_uid(session, uid)
                user_id = user.id
        except NotFoundError:
            # токен валиден, но пользователь уже удалён — считаем как анонима
            return False

        has_consent = await ConsentCacheService.get(user_id)

        if has_consent is None:
            async for session in db_helper.session_getter():
                has_consent = await has_user_consent(session, user_id)
            await ConsentCacheService.set(user_id, has_consent)

        return has_consent

    def _check_anonymous_consent(self, request: Request) -> bool:
        """
        Проверяет согласие анонимного пользователя.
        Флаг живёт в Redis-сессии, которую уже загрузил SessionMiddleware.
        При первом визите проверяет cookie/заголовок и сохраняет в сессию.
        """
        redis_session = request.scope.get("redis_session", {})
        has_consent = redis_session.get("privacy_consent", False)

        if not has_consent:
            has_consent = self._extract_consent_from_request(request)
            if has_consent:
                redis_session["privacy_consent"] = True

        return has_consent

    def _extract_consent_from_request(self, request: Request) -> bool:
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
