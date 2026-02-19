import json
from typing import Callable, Any

from fastapi import HTTPException, Request, status
from starlette.middleware.base import BaseHTTPMiddleware

from src.app.core import db_helper
from src.app.core.logger import get_logger
from src.app.core.repo.privacy_consent import has_user_consent

log = get_logger("privacy_consent_middleware")


class PrivacyConsentMiddleware(BaseHTTPMiddleware):
    """Middleware для проверки согласия на обработку персональных данных"""

    # Пути, которые не требуют проверки согласия
    EXEMPT_PATHS = {
        "/",  # Главная страница
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
        "/privacy/consent",  # Эндпоинт для сохранения согласия
        "/privacy/consent/status",  # Эндпоинт для проверки статуса
        "/auth/login",
        "/auth/register",
        "/auth/logout",
        "/auth/refresh",
    }

    async def dispatch(self, request: Request, call_next: Callable) -> Any | None:
        """
        Проверяет наличие согласия на обработку персональных данных.

        Для авторизованных пользователей проверяет наличие согласия в БД.
        Для неавторизованных пользователей проверяет наличие согласия в localStorage
        через заголовок или cookie.
        """
        path = request.url.path

        # Пропускаем исключенные пути
        if any(path.startswith(exempt_path) for exempt_path in self.EXEMPT_PATHS):
            return await call_next(request)

        # Добавляем сессию БД в request scope
        async for session in db_helper.session_getter():
            request.scope["db_session"] = session

            # Проверяем согласие в зависимости от типа пользователя
            user = getattr(request.state, "user", None)

            if user:
                # Авторизованный пользователь - проверяем в БД
                has_consent = await has_user_consent(session, user.id)
            else:
                # Неавторизованный пользователь - проверяем через заголовок/cookie
                has_consent = await self._check_anonymous_consent(request)

            # Если согласия нет, возвращаем ошибку
            if not has_consent:
                log.warning(
                    "Попытка доступа без согласия на обработку данных: %s, IP: %s, User-Agent: %s",
                    path,
                    request.client.host,
                    request.headers.get("user-agent", "unknown"),
                )
                raise HTTPException(
                    status_code=status.HTTP_451_UNAVAILABLE_FOR_LEGAL_REASONS,
                    detail={
                        "message": "Требуется согласие на обработку персональных данных",
                        "code": "privacy_consent_required",
                        "redirect_url": "/privacy",
                    },
                )

            return await call_next(request)

    async def _check_anonymous_consent(self, request: Request) -> bool:
        """Проверяет наличие согласия для неавторизованного пользователя"""
        try:
            # Проверяем заголовок X-Privacy-Consent
            consent_header = request.headers.get("X-Privacy-Consent")
            if consent_header:
                try:
                    consent_data = json.loads(consent_header)
                    return consent_data.get("personal_data", False)
                except json.JSONDecodeError:
                    pass

            # Проверяем cookie
            consent_cookie = request.cookies.get("privacy_consent")
            if consent_cookie:
                try:
                    consent_data = json.loads(consent_cookie)
                    return consent_data.get("personal_data", False)
                except json.JSONDecodeError:
                    pass

            return False
        except Exception as e:
            log.error(
                "Ошибка при проверке согласия анонимного пользователя: %s", str(e)
            )
            return False
