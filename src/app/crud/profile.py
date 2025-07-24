from fastapi import HTTPException, status
from sqlalchemy import update, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.core.logger import get_logger
from src.app.db.models import User
from src.app.schemas.user import UserResponse, UserProfile, UserAccount

log = get_logger("profile_crud")


async def get_user_profile(
    session: AsyncSession,
    user_id: int,
) -> UserAccount:
    """
    Fetches a user's profile information from the database.

    :param session: The current database session.
    :param user_id: The ID of the user to fetch the profile for.
    :return: The user's profile information.
    :raises HTTPException: If the user is not found in the database.
    """
    stmt = select(User).filter(
        User.id == user_id,
        User.is_active == True,
    )
    try:
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        if user is None:
            log.error(
                "User not found in db for user_id: %s",
                user_id,
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": "Пользователь не найден",
                    "user_id": user_id,
                },
            )
        return UserAccount.model_construct(**user.__dict__)

    except SQLAlchemyError as e:
        log.error(
            "Ошибка БД при получении пользователя: %s",
            e)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "field": "DB error",
                "message": "Внутренняя ошибка сервера",
                # "details": str(e),
            },
        )


async def update_user_profile(
    data_in: UserProfile,
    current_user: UserResponse,
    session: AsyncSession,
) -> UserAccount:
    """
    Updates the current authenticated user's profile information in the database.

    :param data_in: The updated user profile information.
    :param current_user: The authenticated user whose profile is to be updated.
    :param session: The current database session.
    :return: The user's updated profile information.
    :raises HTTPException: If the user is not found in the database or
                           if an error occurs during the update.
    """
    update_data = data_in.model_dump()
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
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "field": "Update user profile",
                    "message": "При обновлении профиля произошла ошибка",
                }
            )
        await session.commit()
        # log.info("User updated with name: %s", current_user.username)

        return UserAccount.model_construct(**updated_user.__dict__)

    except SQLAlchemyError as e:
        log.error(
            "Ошибка БД при обновлении профиля пользователя %s: %s",
            current_user.username, e
        )
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "field": "Update user profile",
                "message": "Внутренняя ошибка сервера",
                # "details": str(e),
            },
        )
