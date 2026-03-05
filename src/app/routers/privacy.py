"""API для работы с согласием на обработку персональных данных"""

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Request

from src.app.core.dependencies import db_session_dep
from src.app.core.logger import get_logger
from src.app.core.schemas.user import UserPublic
from src.app.core.utils.user import optional_current_user
from src.app.core.schemas.privacy import (
    ConsentStatusResponse,
    PrivacyConsentRequest,
    PrivacyConsentResponse,
)
from src.app.core.services.privacy_service import PrivacyService, get_privacy_service

log = get_logger("privacy_router")

# Алиасы типов зависимостей
optional_user_dep = Annotated[Optional[UserPublic], Depends(optional_current_user())]
privacy_service_dep = Annotated[PrivacyService, Depends(get_privacy_service)]

router = APIRouter(
    tags=["Privacy"],
)


@router.post("/consent")
async def save_privacy_consent(
    request: Request,
    consent_data: PrivacyConsentRequest,
    session: db_session_dep,
    user: optional_user_dep,
    privacy_service: privacy_service_dep,
) -> PrivacyConsentResponse:
    """
    Сохраняет согласие на обработку персональных данных.

    Для авторизованных пользователей сохраняет в БД с привязкой к user_id.
    Для неавторизованных пользователей сохраняет в БД с привязкой к session_id.
    """
    try:
        await privacy_service.save_consent(
            request=request,
            session=session,
            user=user,
            consent_data=consent_data,
        )

        await session.commit()

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
    session: db_session_dep,
    user: optional_user_dep,
    privacy_service: privacy_service_dep,
) -> ConsentStatusResponse:
    """
    Возвращает текущий статус согласия на обработку персональных данных.
    """
    try:
        consent_data = await privacy_service.get_consent_status(
            request=request,
            session=session,
            user=user,
        )

        return ConsentStatusResponse(**consent_data)

    except Exception as e:
        log.error("Ошибка при получении статуса согласия: %s", str(e))
        return ConsentStatusResponse(
            personal_data=False, cookies=False, marketing=False, has_consent=False
        )
