"""Функции доступа к данным профиля пользователя (репозиторий)."""

from sqlalchemy import select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.core.exceptions import DatabaseError, NotFoundError
from src.app.core.logger import get_logger
from src.app.core.models import User
from src.app.core.schemas.user import UserProfile, UserProfileUpdate, UserPublic

log = get_logger("profile_repo")


async def get_user_profile(
    session: AsyncSession,
    user_id: int,
) -> UserProfile:
    """
    Получает информацию о профиле пользователя из базы данных.

    :param session: Текущая сессия базы данных.
    :param user_id: ID пользователя для получения профиля.
    :return: Информация о профиле пользователя.
    :raises DatabaseError: Если пользователь не найден в базе данных.
    """

    stmt = select(User).filter(
        User.id == user_id,
        User.is_active.is_(True),
    )
    try:
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        if user is None:
            log.error(
                "User not found in db for user_id: %s",
                user_id,
            )
            raise NotFoundError("Пользователь не найден", resource_type="user")
        return UserProfile.model_validate(user, from_attributes=True)

    except SQLAlchemyError as e:
        log.error("Ошибка БД при получении пользователя: %s", e)
        raise DatabaseError("Внутренняя ошибка сервера", original_error=e)


async def update_user_profile(
    data_in: UserProfileUpdate,
    current_user: UserPublic,
    session: AsyncSession,
) -> UserProfile:
    """
    Обновляет информацию о профиле текущего аутентифицированного пользователя в базе данных.

    :param data_in: Обновленная информация о профиле пользователя.
    :param current_user: Аутентифицированный пользователь, чей профиль нужно обновить.
    :param session: Текущая сессия базы данных.
    :return: Обновленная информация о профиле пользователя.
    :raises DatabaseError: Если пользователь не найден в базе данных или
                           если произошла ошибка во время обновления.
    """

    # обновляем только переданные поля
    update_data = data_in.model_dump(exclude_unset=True)

    try:
        stmt = (
            update(User)
            .where(User.id == current_user.id)
            .values(**update_data)
            .returning(User)
        )

        result = await session.execute(stmt)
        updated_user = result.scalar_one_or_none()

        if updated_user is None:
            log.error(
                "Ошибка обновления профиля для %s",
                current_user,
            )
            raise DatabaseError("При обновлении профиля произошла ошибка")
        await session.commit()

        # возвращаем через pydantic-валидацию, используя атрибуты orm
        return UserProfile.model_validate(updated_user, from_attributes=True)

    except SQLAlchemyError as e:
        log.error(
            "Ошибка БД при обновлении профиля пользователя %s: %s",
            current_user.username,
            e,
        )
        await session.rollback()
        raise DatabaseError("Внутренняя ошибка сервера", original_error=e)
