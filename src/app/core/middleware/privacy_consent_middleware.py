"""
Улучшенный мидлвари для проверки согласия на обработку данных с кешированием
"""

from fastapi import HTTPException, Request, Response, status
from starlette.middleware.base import RequestResponseEndpoint
from starlette.types import ASGIApp

from src.app.core import db_helper
from src.app.core.middleware.base_middleware import BaseMiddleware
from src.app.core.services.middleware_service import privacy_service, tracing_service


class PrivacyConsentV2Middleware(BaseMiddleware):
    """Улучшенный middleware для проверки согласия на обработку персональных данных"""

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
                    # авторизованный пользователь - проверяем в БД с кешированием
                    has_consent = await privacy_service.check_user_consent(
                        user.id, session
                    )
                else:
                    # неавторизованный пользователь - проверяем через заголовок/cookie
                    has_consent = privacy_service.check_anonymous_consent(request)

                # если согласия нет, возвращаем ошибку
                if not has_consent:
                    context = tracing_service.get_request_context(request)
                    tracing_service.log_middleware_error(
                        self.__class__.__name__,
                        context,
                        Exception("Privacy consent required"),
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
            context = tracing_service.get_request_context(request)
            tracing_service.log_middleware_error(self.__class__.__name__, context, e)
            # в случае ошибки БД, продолжаем выполнение запроса для доступности сервиса
            return await call_next(request)
