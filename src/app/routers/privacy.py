"""API для работы с согласием на обработку персональных данных"""

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.core import db_helper
from src.app.core.config import settings
from src.app.core.logger import get_logger
from src.app.core.models.privacy_consent import ConsentType
from src.app.core.utils.network import get_client_ip
from src.app.core.repo.privacy_consent import (
    create_privacy_consent,
    get_user_consents,
    get_session_consents,
    has_user_consent,
    has_session_consent,
)
from src.app.core.schemas.user import UserPublic
from src.app.core.utils.user import optional_current_user
from src.app.core.schemas.privacy import (
    ConsentStatusResponse,
    PrivacyConsentRequest,
    PrivacyConsentResponse,
)

log = get_logger("privacy_router")

# Алиасы типов зависимостей
session_dep = Annotated[AsyncSession, Depends(db_helper.session_getter)]
optional_user_dep = Annotated[Optional[UserPublic], Depends(optional_current_user())]

router = APIRouter(
    tags=["Privacy"],
)


@router.post("/consent")
async def save_privacy_consent(
    request: Request,
    consent_data: PrivacyConsentRequest,
    session: session_dep,
    user: optional_user_dep,
) -> PrivacyConsentResponse:
    """
    Сохраняет согласие на обработку персональных данных.

    Для авторизованных пользователей сохраняет в БД с привязкой к user_id.
    Для неавторизованных пользователей сохраняет в БД с привязкой к session_id.
    """
    try:
        # Получаем информацию о сессии
        redis_session = request.scope.get("redis_session", {})
        session_id = redis_session.get("redis_session_id")

        # Получаем IP и User-Agent
        ip_address = getattr(request.state, "client_ip", None) or get_client_ip(
            request, trusted_proxies=settings.run.trusted_proxies
        )
        user_agent = request.headers.get("user-agent", "unknown")

        # Сохраняем согласие на персональные данные
        if consent_data.personal_data:
            await create_privacy_consent(
                session=session,
                user_id=user.id if user else None,
                session_id=session_id if not user else None,
                ip_address=ip_address,
                user_agent=user_agent,
                consent_type=ConsentType.PERSONAL_DATA,
                is_granted=True,
            )

        # Сохраняем согласие на cookies
        if consent_data.cookies:
            await create_privacy_consent(
                session=session,
                user_id=user.id if user else None,
                session_id=session_id if not user else None,
                ip_address=ip_address,
                user_agent=user_agent,
                consent_type=ConsentType.COOKIES,
                is_granted=True,
            )

        # Сохраняем согласие на маркетинг
        if consent_data.marketing:
            await create_privacy_consent(
                session=session,
                user_id=user.id if user else None,
                session_id=session_id if not user else None,
                ip_address=ip_address,
                user_agent=user_agent,
                consent_type=ConsentType.MARKETING,
                is_granted=True,
            )

        await session.commit()

        log.info(
            "Сохранено согласие на обработку данных: user_id=%s, session_id=%s, ip=%s",
            user.id if user else None,
            session_id,
            ip_address,
        )

        return PrivacyConsentResponse(
            success=True, message="Согласие успешно сохранено"
        )

    except Exception as e:
        await session.rollback()
        log.error("Ошибка при сохранении согласия: %s", str(e))
        raise


@router.get("/consent/status")
async def get_consent_status(
    request: Request,
    session: session_dep,
    user: optional_user_dep,
) -> ConsentStatusResponse:
    """
    Возвращает текущий статус согласия на обработку персональных данных.
    """
    try:
        # Получаем информацию о сессии
        redis_session = request.scope.get("redis_session", {})
        session_id = redis_session.get("redis_session_id")

        if user:
            # Проверяем согласие для авторизованного пользователя
            consents = await get_user_consents(session, user.id)

            # Проверяем наличие каждого типа согласия
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
            # Проверяем согласие для неавторизованного пользователя
            consents = await get_session_consents(session, session_id)

            # Проверяем наличие каждого типа согласия
            personal_data_consent = await has_session_consent(
                session, session_id, ConsentType.PERSONAL_DATA
            )
            cookies_consent = await has_session_consent(
                session, session_id, ConsentType.COOKIES
            )
            marketing_consent = await has_session_consent(
                session, session_id, ConsentType.MARKETING
            )

        # Формируем ответ
        last_updated = consents[0].granted_at if consents else None

        return ConsentStatusResponse(
            personal_data=personal_data_consent,
            cookies=cookies_consent,
            marketing=marketing_consent,
            has_consent=len(consents) > 0,
            last_updated=last_updated,
        )

    except Exception as e:
        log.error("Ошибка при получении статуса согласия: %s", str(e))
        return ConsentStatusResponse(
            personal_data=False, cookies=False, marketing=False, has_consent=False
        )
