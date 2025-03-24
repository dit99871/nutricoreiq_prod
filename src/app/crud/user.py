from typing import Annotated

from fastapi import Depends, status
from fastapi.exceptions import HTTPException
from pydantic import EmailStr
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from core.logger import get_logger
from db import db_helper
from models.user import User
from schemas.user import UserSchema
from utils import (
    get_password_hash,
    log_user_result,
)

log = get_logger(__name__)


async def _get_user_by_filter(
    db: Annotated[AsyncSession, Depends(db_helper.session_getter)],
    filter_condition,
) -> User | None:
    """Вспомогательная функция для получения пользователя по фильтру."""
    try:
        result = await db.execute(
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


async def get_user_by_email(
    db: Annotated[AsyncSession, Depends(db_helper.session_getter)],
    email: EmailStr,
) -> User | None:
    """Получение пользователя по email."""
    try:
        user = await _get_user_by_filter(db, User.email == email)
        log_user_result(
            user,
            log,
            f"User found with email: {email}",
            f"User not found with email: {email}",
        )
        return user
    except HTTPException as e:
        raise e
    except Exception as e:
        log.exception("Unexpected error getting user by email: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error getting user by email: {str(e)}",
        )


async def get_user_by_name(
    db: Annotated[AsyncSession, Depends(db_helper.session_getter)],
    user_name: str,
) -> User | None:
    """Получение пользователя по имени."""
    try:
        user = await _get_user_by_filter(db, User.username == user_name)
        log_user_result(
            user,
            log,
            f"User found with user_name: {user_name}",
            f"User not found with user_name: {user_name}",
        )
        return user
    except HTTPException as e:
        raise e
    except Exception as e:
        log.exception("Unexpected error getting user by name: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error getting user by name: {str(e)}",
        )


async def create_user(
    db: Annotated[AsyncSession, Depends(db_helper.session_getter)],
    user_in: UserSchema,
) -> User | None:
    """Создание нового пользователя."""
    try:
        hashed_password = get_password_hash(user_in.hashed_password)
        db_user = User(
            **user_in.model_dump(
                exclude={"hashed_password"},
                # exclude_defaults=True,
            ),
            hashed_password=hashed_password,
        )
        db.add(db_user)
        await db.commit()
        await db.refresh(db_user)
        log.info("User created with email: %s", user_in.email)
        return db_user
    except SQLAlchemyError as e:
        log.error("Database error creating user_in with email %s: %s", user_in.email, e)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
    except Exception as e:
        log.exception(
            "Unexpected error creating user_in with email %s: %s", user_in.email, e
        )
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


# async def update_user(
#     db: Annotated[AsyncSession, Depends(db_helper.session_getter)],
#     user_email: EmailStr,
#     user: UserUpdate,
# ) -> Optional[User]:
#     """Обновление данных пользователя."""
#     try:
#         db_user = await get_user_by_email(db, user_email)
#         if db_user:
#             for key, value in user.model_dump().items():
#                 if value is not None:
#                     setattr(db_user, key, value)
#             await db.commit()
#             await db.refresh(db_user)
#             log.info("User updated with email: %s", user_email)
#             return db_user
#         log.warning("User not found for update with email: %s", user_email)
#         return None
#     except SQLAlchemyError as e:
#         log.error("Database error updating user with email %s: %s", user_email, e)
#         await db.rollback()
#         return None
#     except Exception as e:
#         log.exception("Unexpected error updating user with email %s: %s", user_email, e)
#         await db.rollback()
#         return None
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
