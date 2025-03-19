from typing import Annotated, Optional

from fastapi import Depends
from pydantic import EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import SQLAlchemyError

from models import db_helper, DeletedUser, User
from schemas import UserCreate, UserUpdate
from core.utils.security import get_password_hash
from core.logger import get_logger

# Настройка логирования
log = get_logger(__name__)


async def _get_user_by_filter(
    db: Annotated[AsyncSession, Depends(db_helper.session_getter)],
    filter_condition,
) -> Optional[User]:
    """Вспомогательная функция для получения пользователя по фильтру."""
    try:
        result = await db.execute(
            select(User).filter(filter_condition, User.is_active is True)
        )
        return result.scalars().first()
    except SQLAlchemyError as e:
        log.error("Database error getting user: %s", e)
        raise  # Перебрасываем исключение
    except Exception as e:
        log.exception("Unexpected error getting user: %s", e)
        raise  # Пробрасываем исключение


async def _log_user_result(
    user: Optional[User],
    success_message: str,
    not_found_message: str,
) -> Optional[User]:
    """Обрабатывает результат запроса пользователя и логирует сообщение."""
    if user:
        log.info(success_message)
    else:
        log.warning(not_found_message)
    return user


async def get_user_by_id(
    db: Annotated[AsyncSession, Depends(db_helper.session_getter)],
    user_id: int,
) -> Optional[User]:
    """Получение пользователя по ID."""
    user = await _get_user_by_filter(db, User.id == user_id)
    return await _log_user_result(
        user,
        f"User found with id: {user_id}",
        f"User not found with id: {user_id}",
    )


async def get_user_by_email(
    db: Annotated[AsyncSession, Depends(db_helper.session_getter)],
    email: EmailStr,
) -> Optional[User]:
    """Получение пользователя по email."""
    user = await _get_user_by_filter(db, User.email == email)
    return await _log_user_result(
        user,
        f"User found with email: {email}",
        f"User not found with email: {email}",
    )


async def get_user_by_name(
    db: Annotated[AsyncSession, Depends(db_helper.session_getter)],
    user_name: str,
) -> Optional[User]:
    user = await _get_user_by_filter(db, User.username == user_name)
    return await _log_user_result(
        user,
        f"User found with user_name: {user_name}",
        f"User not found with user_name: {user_name}",
    )


async def create_user(
    db: Annotated[AsyncSession, Depends(db_helper.session_getter)],
    user: UserCreate,
) -> Optional[User]:
    """Создание нового пользователя."""
    try:
        hashed_password = get_password_hash(user.password)
        db_user = User(
            username=user.username,
            email=user.email,
            hashed_password=hashed_password,
            gender=user.gender,
            age=user.age,
            weight=user.weight,
        )
        db.add(db_user)
        await db.commit()
        await db.refresh(db_user)
        log.info("User created with email: %s", user.email)
        return db_user
    except SQLAlchemyError as e:
        log.error("Database error creating user with email %s: %s", user.email, e)
        await db.rollback()
        return None
    except Exception as e:
        log.exception("Unexpected error creating user with email %s: %s", user.email, e)
        await db.rollback()
        return None


async def update_user(
    db: Annotated[AsyncSession, Depends(db_helper.session_getter)],
    user_email: EmailStr,
    user: UserUpdate,
) -> Optional[User]:
    """Обновление данных пользователя."""
    try:
        db_user = await get_user_by_email(db, user_email)
        if db_user:
            for key, value in user.model_dump().items():
                if value is not None:
                    setattr(db_user, key, value)
            await db.commit()
            await db.refresh(db_user)
            log.info("User updated with email: %s", user_email)
            return db_user
        log.warning("User not found for update with email: %s", user_email)
        return None
    except SQLAlchemyError as e:
        log.error("Database error updating user with email %s: %s", user_email, e)
        await db.rollback()
        return None
    except Exception as e:
        log.exception("Unexpected error updating user with email %s: %s", user_email, e)
        await db.rollback()
        return None


async def delete_user(
    db: Annotated[AsyncSession, Depends(db_helper.session_getter)], user_email: EmailStr
) -> Optional[DeletedUser]:
    """Удаление пользователя."""
    try:
        db_user = await get_user_by_email(db, user_email)
        if db_user:
            # Создаем запись в таблице deleted_users
            deleted_user = DeletedUser(
                username=db_user.username,
                email=db_user.email,
                hashed_password=db_user.hashed_password,
                gender=db_user.gender,
                age=db_user.age,
                weight=db_user.weight,
                is_active=db_user.is_active,
            )
            db.add(deleted_user)
            await db.commit()
            await db.refresh(deleted_user)

            # Удаляем пользователя из таблицы users
            await db.delete(db_user)
            await db.commit()
            log.info("User deleted with email: %s", user_email)
            return deleted_user
        log.warning("User not found for deletion with email: %s", user_email)
        return None
    except SQLAlchemyError as e:
        log.error("Database error deleting user with email %s: %s", user_email, e)
        await db.rollback()
        return None
    except Exception as e:
        log.exception("Unexpected error deleting user with email %s: %s", user_email, e)
        await db.rollback()
        return None
