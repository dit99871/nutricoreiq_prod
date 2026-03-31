"""Сервис для работы с согласиями на обработку персональных данных"""

from typing import Optional

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.core.config import settings
from src.app.core.logger import get_logger
from src.app.core.models.privacy_consent import ConsentType
from src.app.core.repo.privacy_consent import (
    create_privacy_consent,
    get_user_consents,
    get_session_consents,
    has_user_consent,
    has_session_consent,
)
from src.app.core.schemas.user import UserPublic
from src.app.core.services.cache import ConsentCacheService
from src.app.core.utils.network import get_client_ip

log = get_logger("privacy_service")


class PrivacyService:
    """Сервис для работы с согласиями на обработку персональных данных."""

    @staticmethod
    async def save_consent(
        request: Request,
        session: AsyncSession,
        user: Optional[UserPublic],
        consent_data,
    ) -> None:
        """
        Сохраняет согласие на обработку персональных данных.

        Для авторизованных пользователей сохраняет в БД с привязкой к user_id.
        Для неавторизованных пользователей сохраняет в БД с привязкой к session_id.
        """
        # получаем информацию о сессии
        redis_session = request.scope.get("redis_session", {})
        session_id = redis_session.get("redis_session_id")

        # получаем ip и ua
        ip_address = getattr(request.state, "client_ip", None) or get_client_ip(
            request, trusted_proxies=settings.run.trusted_proxies
        )
        user_agent = request.headers.get("user-agent", "unknown")

        # определяем параметры для сохранения
        user_id = user.id if user else None
        session_param = session_id if not user else None

        # сохраняем согласия
        consent_types = []
        if consent_data.personal_data:
            consent_types.append(ConsentType.PERSONAL_DATA)
        if consent_data.cookies:
            consent_types.append(ConsentType.COOKIES)
        if consent_data.marketing:
            consent_types.append(ConsentType.MARKETING)

        for consent_type in consent_types:
            await create_privacy_consent(
                session=session,
                user_id=user_id,
                session_id=session_param,
                ip_address=ip_address,
                user_agent=user_agent,
                consent_type=consent_type,
                is_granted=True,
            )

            # инвалидируем кеш согласия для авторизованного пользователя,
            # чтобы middleware при следующем запросе перечитал актуальные данные из БД
            if user_id:
                await ConsentCacheService.invalidate(user_id)

        log.info(
            "Сохранено согласие на обработку данных: user_id=%s, session_id=%s, ip=%s",
            user_id,
            session_param,
            ip_address,
        )

    @staticmethod
    async def get_consent_status(
        request: Request,
        session: AsyncSession,
        user: Optional[UserPublic],
    ) -> dict:
        """
        Возвращает текущий статус согласия на обработку персональных данных.
        """

        # получаем информацию о сессии
        redis_session = request.scope.get("redis_session", {})
        session_id = redis_session.get("redis_session_id")

        if user:
            # проверяем согласие для авторизованного пользователя
            consents = await get_user_consents(session, user.id)

            # проверяем наличие каждого типа согласия
            personal_data_consent = await has_user_consent(
                session, user.id, ConsentType.PERSONAL_DATA
            )
            cookies_consent = await has_user_consent(
                session, user.id, ConsentType.COOKIES
            )
            marketing_consent = await has_user_consent(
                session, user.id, ConsentType.MARKETING
            )
        else:
            # проверяем согласие для неавторизованного пользователя
            consents = await get_session_consents(session, session_id)

            # проверяем наличие каждого типа согласия
            personal_data_consent = await has_session_consent(
                session, session_id, ConsentType.PERSONAL_DATA
            )
            cookies_consent = await has_session_consent(
                session, session_id, ConsentType.COOKIES
            )
            marketing_consent = await has_session_consent(
                session, session_id, ConsentType.MARKETING
            )

        # формируем ответ
        last_updated = consents[0].granted_at if consents else None

        return {
            "personal_data": personal_data_consent,
            "cookies": cookies_consent,
            "marketing": marketing_consent,
            "has_consent": len(consents) > 0,
            "last_updated": last_updated,
        }


def get_privacy_service() -> PrivacyService:
    """Возвращает экземпляр PrivacyService."""

    return PrivacyService()
