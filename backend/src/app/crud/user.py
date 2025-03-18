from typing import Annotated, Optional

from fastapi import Depends
from pydantic import EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import SQLAlchemyError

from app.core.models import DeletedUser, User
from app.core.schemas import UserCreate, UserUpdate
from app.utils.security import get_password_hash
from app.utils.logger import get_logger
from core.models import db_helper

# Настройка логирования
log = get_logger(__name__)


async def _get_user_by_filter(
    db: Annotated[AsyncSession, Depends(db_helper.session_getter)],
    filter_condition,
) -> Optional[User]:
    """Вспомогательная функция для получения пользователя по фильтру."""
    try:
        result = await db.execute(
            select(User).filter(filter_condition, User.is_active == True)
        )
        return result.scalars().first()
    except SQLAlchemyError as e:
        log.error(f"Database error getting user: {e}")
        raise  # Перебрасываем исключение
    except Exception as e:
        log.exception(f"Unexpected error getting user: {e}")
        raise  # Пробрасываем исключение


async def _handle_user_result(
    user: Optional[User], success_message: str, not_found_message: str
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
    return await _handle_user_result(
        user, f"User found with id: {user_id}", f"User not found with id: {user_id}"
    )


async def get_user_by_email(
    db: Annotated[AsyncSession, Depends(db_helper.session_getter)],
    email: EmailStr,
) -> Optional[User]:
    """Получение пользователя по email."""
    user = await _get_user_by_filter(db, User.email == email)
    return await _handle_user_result(
        user,
        f"User found with email: {email}",
        f"User not found with email: {email}",
    )


async def get_user_by_name(
    db: Annotated[AsyncSession, Depends(db_helper.session_getter)],
    user_name: str,
) -> Optional[User]:
    user = await _get_user_by_filter(db, User.username == user_name)
    return await _handle_user_result(
        user,
        f"User found with user_name: {user_name}",
        f"User not found with user_name: {user_name}"
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
        log.info(f"User created with email: {user.email}")
        return db_user
    except SQLAlchemyError as e:
        log.error(f"Database error creating user with email {user.email}: {e}")
        await db.rollback()
        return None
    except Exception as e:
        log.exception(f"Unexpected error creating user with email {user.email}: {e}")
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
            log.info(f"User updated with email: {user_email}")
            return db_user
        else:
            log.warning(f"User not found for update with email: {user_email}")
            return None
    except SQLAlchemyError as e:
        log.error(f"Database error updating user with email {user_email}: {e}")
        await db.rollback()
        return None
    except Exception as e:
        log.exception(f"Unexpected error updating user with email {user_email}: {e}")
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
            log.info(f"User deleted with email: {user_email}")
            return deleted_user
        else:
            log.warning(f"User not found for deletion with email: {user_email}")
            return None
    except SQLAlchemyError as e:
        log.error(f"Database error deleting user with email {user_email}: {e}")
        await db.rollback()
        return None
    except Exception as e:
        log.exception(f"Unexpected error deleting user with email {user_email}: {e}")
        await db.rollback()
        return None
