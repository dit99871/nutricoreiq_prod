import logging

from pydantic import EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import SQLAlchemyError

from app.core.models import DeletedUser, User
from app.core.schemas import UserCreate, UserUpdate
from app.utils.security import get_password_hash
from app.utils.logger import get_logger

# Настройка логирования
get_logger(__name__)


async def _get_user_by_filter(db: AsyncSession, filter_condition) -> User | None:
    """Вспомогательная функция для получения пользователя по фильтру."""
    try:
        result = await db.execute(
            select(User).filter(filter_condition, User.is_active == True)
        )
        return result.scalars().first()
    except SQLAlchemyError as e:
        logging.error(f"Database error getting user: {e}")
        raise  # Перебрасываем исключение
    except Exception as e:
        logging.exception(f"Unexpected error getting user: {e}")
        raise  # Пробрасываем исключение


async def get_user(db: AsyncSession, user_id: int) -> User | None:
    """Получение пользователя по ID."""
    user = await _get_user_by_filter(db, User.id == user_id)
    if user:
        logging.info(f"User found with id: {user_id}")
    else:
        logging.warning(f"User not found with id: {user_id}")
    return user


async def get_user_by_email(db: AsyncSession, email: EmailStr) -> User | None:
    """Получение пользователя по email."""
    user = await _get_user_by_filter(db, User.email == email)
    if user:
        logging.info(f"User found with email: {email}")
    else:
        logging.warning(f"User not found with email: {email}")
    return user


async def create_user(db: AsyncSession, user: UserCreate) -> User | None:
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
        logging.info(f"User created with email: {user.email}")
        return db_user
    except SQLAlchemyError as e:
        logging.error(f"Database error creating user with email {user.email}: {e}")
        await db.rollback()
        return None
    except Exception as e:
        logging.exception(
            f"Unexpected error creating user with email {user.email}: {e}"
        )
        await db.rollback()
        return None


async def update_user(
    db: AsyncSession, user_email: EmailStr, user: UserUpdate
) -> User | None:
    """Обновление данных пользователя."""
    try:
        db_user = await get_user_by_email(db, user_email)
        if db_user:
            for key, value in user.model_dump().items():
                if value is not None:
                    setattr(db_user, key, value)
            await db.commit()
            await db.refresh(db_user)
            logging.info(f"User updated with email: {user_email}")
            return db_user
        else:
            logging.warning(f"User not found for update with email: {user_email}")
            return None
    except SQLAlchemyError as e:
        logging.error(f"Database error updating user with email {user_email}: {e}")
        await db.rollback()
        return None
    except Exception as e:
        logging.exception(
            f"Unexpected error updating user with email {user_email}: {e}"
        )
        await db.rollback()
        return None


async def delete_user(db: AsyncSession, user_email: EmailStr) -> DeletedUser | None:
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
                is_admin=db_user.is_admin,
            )
            db.add(deleted_user)
            await db.commit()
            await db.refresh(deleted_user)

            # Удаляем пользователя из таблицы users
            await db.delete(db_user)
            await db.commit()
            logging.info(f"User deleted with email: {user_email}")
            return deleted_user
        else:
            logging.warning(f"User not found for deletion with email: {user_email}")
            return None
    except SQLAlchemyError as e:
        logging.error(f"Database error deleting user with email {user_email}: {e}")
        await db.rollback()
        return None
    except Exception as e:
        logging.exception(
            f"Unexpected error deleting user with email {user_email}: {e}"
        )
        await db.rollback()
        return None
