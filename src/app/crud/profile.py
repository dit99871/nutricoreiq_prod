from fastapi import HTTPException, status
from sqlalchemy import update, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.core.logger import get_logger
from src.app.models import User
from src.app.models.user import KFALevel, GoalType
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
        log.error("Ошибка БД при получении пользователя: %s", e)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "field": "DB error",
                "message": "Внутренняя ошибка сервера",
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
        kfa_val = update_data.get("kfa")
        if kfa_val is not None:
            if kfa_val == "":
                update_data["kfa"] = None
            else:
                # Найти enum по value ("1".."5")
                update_data["kfa"] = next(
                    (m for m in KFALevel if m.value == str(kfa_val)), None
                )
                if update_data["kfa"] is None:
                    raise ValueError(f"Недопустимое значение kfa: {kfa_val}")

        goal_val = update_data.get("goal")
        if goal_val is not None:
            if goal_val == "":
                update_data["goal"] = None
            else:
                # GoalType значения — русские строки; получаем enum по value
                update_data["goal"] = GoalType(goal_val)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "field": "profile",
                "message": str(e),
            },
        )

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
                },
            )
        await session.commit()

        return UserAccount.model_construct(**updated_user.__dict__)

    except SQLAlchemyError as e:
        log.error(
            "Ошибка БД при обновлении профиля пользователя %s: %s",
            current_user.username,
            e,
        )
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "field": "Update user profile",
                "message": "Внутренняя ошибка сервера",
            },
        )
