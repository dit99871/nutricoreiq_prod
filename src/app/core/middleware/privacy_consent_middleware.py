import json

from fastapi import HTTPException, Request, Response, status
from starlette.middleware.base import RequestResponseEndpoint
from starlette.types import ASGIApp

from src.app.core import db_helper
from src.app.core.middleware.base_middleware import BaseMiddleware
from src.app.core.repo.privacy_consent import has_user_consent


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
    ) -> Response:
        """Основная логика PrivacyConsent middleware"""

        # пропускаем исключенные пути
        if self._should_skip_path(request, self.EXEMPT_PATHS):
            return await call_next(request)

        try:
            # добавляем сессию БД в request scope
            async for session in db_helper.session_getter():
                request.scope["db_session"] = session

                # проверяем согласие в зависимости от типа пользователя
                user = getattr(request.state, "user", None)

                if user:
                    # авторизованный пользователь - проверяем в БД
                    has_consent = await has_user_consent(session, user.id)
                else:
                    # неавторизованный пользователь - проверяем через заголовок/cookie
                    has_consent = await self._check_anonymous_consent(request)

                # если согласия нет, возвращаем ошибку
                if not has_consent:
                    context = self._get_request_context(request)
                    self.logger.warning(
                        "Попытка доступа без согласия на обработку данных: %s, IP: %s, User-Agent: %s",
                        context["url"],
                        context["client_ip"],
                        context["user_agent"],
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

        except HTTPException:
            # пробрасываем HTTP исключения дальше
            raise

        except Exception as e:
            # Логируем ошибки БД и другие непредвиденные ошибки
            context = self._get_request_context(request)
            self.logger.error(
                "Ошибка в PrivacyConsentMiddleware: %s, IP: %s, User-Agent: %s",
                str(e),
                context["client_ip"],
                context["user_agent"],
                exc_info=True,
            )
            # в случае ошибки БД, продолжаем выполнение запроса для доступности сервиса
            return await call_next(request)

    async def _check_anonymous_consent(self, request: Request) -> bool:
        """Проверяет наличие согласия для неавторизованного пользователя"""
        try:
            # проверяем заголовок X-Privacy-Consent
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
            self.logger.error(
                "Ошибка при проверке согласия анонимного пользователя: %s", str(e)
            )
            return False
