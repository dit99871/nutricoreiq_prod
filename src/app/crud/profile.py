from fastapi import HTTPException, status
from sqlalchemy import update, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from core.logger import get_logger
from db.models import User
from schemas.user import UserResponse, UserProfile, UserBase

log = get_logger("profile_crud")


async def get_user_profile(
    session: AsyncSession,
    user_id: int,
) -> UserBase:
    stmt = select(User).filter(
        User.id == user_id,
        User.is_active == True,
    )
    try:
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        if user is None:
            log.error("User not found in db for user_id: %s", user_id)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User not found in db for user_id {user_id}",
            )
        return UserBase.model_validate(user, from_attributes=True)

    except SQLAlchemyError as e:
        log.error("Database error getting user: %s", e)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"DB error getting user: {str(e)}",
        )

    except Exception as e:
        log.exception("Unexpected error getting user from db: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error getting user {str(e)}",
        )


async def update_user_profile(
    data_in: UserProfile,
    current_user: UserResponse,
    session: AsyncSession,
):
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

        if not updated_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not updated"
            )

        await session.commit()
        log.info("User updated with name: %s", current_user.username)

        return

    except SQLAlchemyError as e:
        log.error(
            "Database error updating user with name %s: %s", current_user.username, e
        )
        await session.rollback()
        return None
    except Exception as e:
        log.exception(
            "Unexpected error updating user with name %s: %s", current_user.username, e
        )
        await session.rollback()
        return None
