from typing import Optional

from fastapi import status
from fastapi.exceptions import HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from src.app.core.logger import get_logger
from src.app.core.models.privacy_consent import ConsentType, PrivacyConsent

log = get_logger("privacy_consent_repo")


async def create_privacy_consent(
    session: AsyncSession,
    user_id: Optional[int],
    session_id: Optional[str],
    ip_address: str,
    user_agent: str,
    consent_type: ConsentType,
    is_granted: bool,
    policy_version: str = "1.0",
) -> PrivacyConsent:
    """
    Создает запись о согласии на обработку персональных данных.

    :param session: Асинхронная сессия SQLAlchemy
    :param user_id: ID пользователя (если авторизован)
    :param session_id: ID сессии (если неавторизован)
    :param ip_address: IP адрес пользователя
    :param user_agent: User Agent браузера
    :param consent_type: Тип согласия
    :param is_granted: Статус согласия
    :param policy_version: Версия политики конфиденциальности
    :return: Созданная запись согласия
    :raises HTTPException: При ошибке базы данных
    """
    try:
        consent = PrivacyConsent(
            user_id=user_id,
            session_id=session_id,
            ip_address=ip_address,
            user_agent=user_agent,
            consent_type=consent_type,
            is_granted=is_granted,
            policy_version=policy_version,
        )

        session.add(consent)
        await session.flush()  # Получаем ID без коммита
        await session.refresh(consent)

        log.info(
            "Создано согласие: user_id=%s, session_id=%s, type=%s, granted=%s",
            user_id,
            session_id,
            consent_type.value,
            is_granted,
        )

        return consent

    except SQLAlchemyError as e:
        log.error("Ошибка при создании согласия: %s", str(e))
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": "Ошибка при сохранении согласия"},
        )


async def has_user_consent(
    session: AsyncSession,
    user_id: int,
    consent_type: ConsentType = ConsentType.PERSONAL_DATA,
) -> bool:
    """
    Проверяет наличие согласия у пользователя.

    :param session: Асинхронная сессия SQLAlchemy
    :param user_id: ID пользователя
    :param consent_type: Тип согласия для проверки
    :return: True если согласие есть, иначе False
    """
    try:
        stmt = (
            select(PrivacyConsent)
            .filter(
                PrivacyConsent.user_id == user_id,
                PrivacyConsent.consent_type == consent_type,
                PrivacyConsent.is_granted == True,
            )
            .order_by(PrivacyConsent.granted_at.desc())
            .limit(1)
        )

        result = await session.execute(stmt)
        consent = result.scalar_one_or_none()

        return consent is not None

    except SQLAlchemyError as e:
        log.error("Ошибка при проверке согласия пользователя: %s", str(e))
        return False


async def has_session_consent(
    session: AsyncSession,
    session_id: str,
    consent_type: ConsentType = ConsentType.PERSONAL_DATA,
) -> bool:
    """
    Проверяет наличие согласия у сессии.

    :param session: Асинхронная сессия SQLAlchemy
    :param session_id: ID сессии
    :param consent_type: Тип согласия для проверки
    :return: True если согласие есть, иначе False
    """
    try:
        stmt = (
            select(PrivacyConsent)
            .filter(
                PrivacyConsent.session_id == session_id,
                PrivacyConsent.consent_type == consent_type,
                PrivacyConsent.is_granted == True,
            )
            .order_by(PrivacyConsent.granted_at.desc())
            .limit(1)
        )

        result = await session.execute(stmt)
        consent = result.scalar_one_or_none()

        return consent is not None

    except SQLAlchemyError as e:
        log.error("Ошибка при проверке согласия сессии: %s", str(e))
        return False


async def get_user_consents(
    session: AsyncSession, user_id: int
) -> list[PrivacyConsent]:
    """
    Получает все согласия пользователя.

    :param session: Асинхронная сессия SQLAlchemy
    :param user_id: ID пользователя
    :return: Список согласий пользователя
    """
    try:
        stmt = (
            select(PrivacyConsent)
            .filter(PrivacyConsent.user_id == user_id)
            .order_by(PrivacyConsent.granted_at.desc())
        )

        result = await session.execute(stmt)
        consents = result.scalars().all()

        return list(consents)

    except SQLAlchemyError as e:
        log.error("Ошибка при получении согласий пользователя: %s", str(e))
        return []


async def get_session_consents(
    session: AsyncSession, session_id: str
) -> list[PrivacyConsent]:
    """
    Получает все согласия сессии.

    :param session: Асинхронная сессия SQLAlchemy
    :param session_id: ID сессии
    :return: Список согласий сессии
    """
    try:
        stmt = (
            select(PrivacyConsent)
            .filter(PrivacyConsent.session_id == session_id)
            .order_by(PrivacyConsent.granted_at.desc())
        )

        result = await session.execute(stmt)
        consents = result.scalars().all()

        return list(consents)

    except SQLAlchemyError as e:
        log.error("Ошибка при получении согласий сессии: %s", str(e))
        return []
