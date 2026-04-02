from typing import Optional

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.app.core.exceptions import DatabaseError
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
    :raises DatabaseError: При ошибке базы данных
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

        log.info(
            "Создано согласие: user_id=%s, session_id=%s, type=%s, granted=%s",
            user_id,
            session_id,
            consent_type.value,
            is_granted,
        )

        return consent

    except SQLAlchemyError as e:
        log.error("Ошибка при создании согласия: %s", e)
        await session.rollback()
        raise DatabaseError("Ошибка при сохранении согласия", original_error=e)


async def _has_consent(
    session: AsyncSession,
    consent_type: ConsentType,
    user_id: Optional[int] = None,
    session_id: Optional[str] = None,
) -> bool:
    """
    Общая функция проверки согласия.

    :param session: Асинхронная сессия SQLAlchemy
    :param consent_type: Тип согласия для проверки
    :param user_id: ID пользователя (опционально)
    :param session_id: ID сессии (опционально)
    :return: True если согласие есть, иначе False
    :raises ValueError: Если не указан ни user_id, ни session_id
    """

    try:
        filters = [
            PrivacyConsent.consent_type == consent_type,
            PrivacyConsent.is_granted == True,
        ]

        if user_id is not None:
            filters.append(PrivacyConsent.user_id == user_id)
        elif session_id is not None:
            filters.append(PrivacyConsent.session_id == session_id)
        else:
            raise ValueError("Нужно указать user_id или session_id")

        stmt = (
            select(PrivacyConsent)
            .filter(*filters)
            .order_by(PrivacyConsent.granted_at.desc())
            .limit(1)
        )

        result = await session.execute(stmt)
        consent = result.scalar_one_or_none()

        return consent is not None

    except SQLAlchemyError as e:
        log.error("Ошибка при проверке согласия: %s", e)
        return False


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

    return await _has_consent(session, consent_type, user_id=user_id)


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

    return await _has_consent(session, consent_type, session_id=session_id)


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
        log.error("Ошибка при получении согласий пользователя: %s", e)
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
        log.error("Ошибка при получении согласий сессии: %s", e)
        return []
