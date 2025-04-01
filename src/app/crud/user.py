from fastapi import status
from fastapi.exceptions import HTTPException
from pydantic import EmailStr
from sqlalchemy import update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from core.logger import get_logger
from db.models import User
from schemas.user import UserCreate, UserResponse, UserProfile
from utils.auth import get_password_hash
from utils.user import log_user_result

log = get_logger("user_crud")


async def _get_user_by_filter(
    session: AsyncSession,
    filter_condition,
) -> User | None:
    try:
        result = await session.execute(
            select(User).filter(filter_condition, User.is_active == True)
        )
        return result.scalars().first()
    except SQLAlchemyError as e:
        log.error("Database error getting user: %s", e)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"DB error getting user: {str(e)}",
        )
    except Exception as e:
        log.exception("Unexpected error getting user: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error getting user {str(e)}",
        )


async def get_user_by_uid(
    session: AsyncSession,
    uid: str,
) -> UserResponse | None:
    try:
        user = await _get_user_by_filter(session, User.uid == uid)
        log_user_result(
            user,
            log,
            f"User found with uid: {uid}",
            f"User not found with uid: {uid}",
        )
        return UserResponse.model_validate(user) if user is not None else None
    except HTTPException as e:
        raise e


async def get_user_by_email(
    session: AsyncSession,
    email: EmailStr,
) -> UserResponse | None:
    try:
        user: User = await _get_user_by_filter(session, User.email == email)
        log_user_result(
            user,
            log,
            f"User found with email: {email}",
            f"User not found with email: {email}",
        )
        return UserResponse.model_validate(user) if user is not None else None
    except HTTPException as e:
        raise e


async def get_user_by_name(
    session: AsyncSession,
    user_name: str,
) -> UserResponse | None:
    try:
        user = await _get_user_by_filter(session, User.username == user_name)
        log_user_result(
            user,
            log,
            f"User found with user_name: {user_name}",
            f"User not found with user_name: {user_name}",
        )
        return UserResponse.model_validate(user) if user is not None else None
    except HTTPException as e:
        raise e


async def create_user(
    session: AsyncSession,
    user_in: UserCreate,
) -> UserCreate | None:
    try:
        hashed_password = get_password_hash(user_in.password)
        db_user = User(
            **user_in.model_dump(
                exclude={"password"},
                exclude_defaults=True,
            ),
            hashed_password=hashed_password,
        )
        session.add(db_user)
        await session.commit()
        await session.refresh(db_user)
        log.info("User created with email: %s", user_in.email)

        return user_in

    except SQLAlchemyError as e:
        log.error("Database error creating user_in with email %s: %s", user_in.email, e)
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )

    except Exception as e:
        log.exception(
            "Unexpected error creating user_in with email %s: %s", user_in.email, e
        )
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
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


#
#
# async def delete_user(
#     db: Annotated[AsyncSession, Depends(db_helper.session_getter)],
#     user_email: EmailStr,
#     user: UserDelete,
# ) -> Optional[DeletedUser]:
#     """Удаление пользователя."""
#     try:
#         db_user = await get_user_by_email(db, user_email)
#         if db_user:
#             # Создаем запись в таблице deleted_users
#             deleted_user = DeletedUser(
#                 username=db_user.username,
#                 email=db_user.email,
#                 hashed_password=db_user.hashed_password,
#                 gender=db_user.gender,
#                 age=db_user.age,
#                 weight=db_user.weight,
#                 is_active=db_user.is_active,
#             )
#             db.add(deleted_user)
#             await db.commit()
#             await db.refresh(deleted_user)
#
#             # Удаляем пользователя из таблицы users
#             await db.delete(db_user)
#             await db.commit()
#             log.info("User deleted with email: %s", user_email)
#             return deleted_user
#         log.warning("User not found for deletion with email: %s", user_email)
#         return None
#     except SQLAlchemyError as e:
#         log.error("Database error deleting user with email %s: %s", user_email, e)
#         await db.rollback()
#         return None
#     except Exception as e:
#         log.exception("Unexpected error deleting user with email %s: %s", user_email, e)
#         await db.rollback()
#         return None
