from pydantic import EmailStr
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.app.core.exceptions import DatabaseError, NotFoundError
from src.app.core.logger import get_logger
from src.app.core.services.cache import CacheService
from src.app.core.utils.auth import get_password_hash
from src.app.core.models import User
from src.app.core.schemas.user import UserCreate, UserPublic

log = get_logger("user_repo")


async def _get_user_by_filter(
    session: AsyncSession,
    filter_condition,
) -> UserPublic | None:
    """
    Получает пользователя из базы данных по заданному фильтру.

    Ищет активного пользователя в базе данных, соответствующего переданному условию фильтрации.
    Возвращает объект пользователя в формате UserPublic, если пользователь найден и активен,
    или None, если пользователь не найден или неактивен.

    :param session: Асинхронная сессия SQLAlchemy для работы с базой данных.
    :param filter_condition: Условие фильтрации для поиска пользователя.
    :return: Объект UserPublic с данными пользователя или None, если пользователь не найден.
    :raises DatabaseError: При возникновении ошибок при работе с базой данных.
    """

    try:
        stmt = select(User).filter(filter_condition, User.is_active == True)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        return UserPublic.model_validate(user) if user else None

    except SQLAlchemyError as e:
        log.error(
            "Database error: %s",
            str(e),
        )
        raise DatabaseError("Внутренняя ошибка сервера", original_error=e)


async def get_user_by_uid(
    session: AsyncSession,
    uid: str,
    use_cache: bool = True,
) -> UserPublic:
    """
    Получает пользователя из базы данных по его UID с возможностью кеширования.

    Ищет пользователя в базе данных по указанному UID. Поддерживает кеширование
    для ускорения последующих запросов. Если пользователь не найден, вызывает
    исключение HTTP 404.

    :param session: Асинхронная сессия SQLAlchemy для работы с базой данных.
    :param uid: UID пользователя для поиска.
    :param use_cache: Флаг использования кеширования (по умолчанию: True).
    :return: Объект UserPublic с данными пользователя.
    :raises NotFoundError: Если пользователь не найден или произошла ошибка.
    """

    # пытаемся получить из кеша
    if use_cache:
        cached_user = await CacheService.get_user(uid)
        if cached_user:
            return UserPublic.model_validate(cached_user)

    # если нет в кеше или кеш отключен, идем в БД
    user = await _get_user_by_filter(session, User.uid == uid)
    if user is None:
        log.error("User not found in db by uid")
        raise NotFoundError("Пользователь не найден", resource_type="user")

    # обновляем кеш
    if use_cache:
        await CacheService.set_user(uid, user.model_dump())

    return user


async def get_user_by_email(
    session: AsyncSession,
    email: EmailStr,
) -> UserPublic | None:
    """
    Получает пользователя из базы данных по email.

    Ищет активного пользователя в базе данных по указанному email.
    Возвращает объект пользователя в формате UserPublic, если пользователь найден,
    или None, если пользователь не найден.

    :param session: Асинхронная сессия SQLAlchemy для работы с базой данных.
    :param email: Email пользователя для поиска.
    :return: Объект UserPublic с данными пользователя или None, если пользователь не найден.
    """

    user = await _get_user_by_filter(session, User.email == email)

    return user


async def get_user_by_name(
    session: AsyncSession,
    user_name: str,
) -> UserPublic:
    """
    Получает пользователя из базы данных по имени пользователя.

    Ищет активного пользователя в базе данных по указанному имени пользователя.
    Возвращает объект пользователя в формате UserPublic, если пользователь найден,
    или вызывает исключение HTTP 404, если пользователь не найден.

    :param session: Асинхронная сессия SQLAlchemy для работы с базой данных.
    :param user_name: Имя пользователя для поиска.
    :return: Объект UserPublic с данными пользователя.
    """

    user = await _get_user_by_filter(session, User.username == user_name)

    return user


async def create_user(
    session: AsyncSession,
    user_in: UserCreate,
) -> UserPublic:
    """
    Создает нового пользователя в базе данных.

    Принимает объект UserCreate, хеширует пароль и создает новую запись пользователя
    в базе данных. В случае успеха возвращает созданного пользователя в формате UserPublic.

    :param session: Асинхронная сессия SQLAlchemy для работы с базой данных.
    :param user_in: Данные для создания нового пользователя.
    :return: Объект UserPublic с данными созданного пользователя.
    :raises DatabaseError: Если произошла ошибка при создании пользователя.
    """

    try:
        hashed_password = get_password_hash(user_in.password)
        db_user = User(
            **user_in.model_dump(
                exclude={"password"},
                # exclude_defaults=True,
            ),
            hashed_password=hashed_password,
        )
        session.add(db_user)
        await session.commit()
        await session.refresh(db_user)

        # возвращаем валидированную pydantic-модель пользователя (без пароля)
        return UserPublic.model_validate(db_user)

    except SQLAlchemyError as e:
        log.error(
            "Database error creating user_in with email %s: %s",
            user_in.email,
            str(e),
        )
        await session.rollback()
        raise DatabaseError("Ошибка при создании пользователя", original_error=e)


async def choose_subscribe_status(
    user: UserPublic,
    session: AsyncSession,
    condition: bool,
):
    """
    Обновляет статус подписки для указанного пользователя.

    Изменяет статус подписки пользователя на указанное значение.
    В случае успешного обновления сохраняет изменения в базе данных.

    :param user: Объект пользователя (UserPublic), для которого обновляется подписка.
    :param session: Асинхронная сессия SQLAlchemy для работы с базой данных.
    :param condition: Булево значение нового статуса подписки.
    :raises NotFoundError: Если пользователь не найден.
    :raises DatabaseError: Если произошла ошибка при обновлении бд.
    """

    stmt = select(User).filter(User.uid == user.uid, User.is_active == True)
    result = await session.execute(stmt)
    target_user = result.scalar_one_or_none()

    if not target_user:
        log.error(
            "Пользователь с uid %s не найден или неактивен",
            user.uid,
        )
        raise NotFoundError("Пользователь не найден", resource_type="user")
    target_user.is_subscribed = condition

    try:
        await session.commit()
        await session.refresh(target_user)
    except SQLAlchemyError as e:
        await session.rollback()
        log.error(
            "Ошибка при фиксации изменений: %s",
            str(e),
        )
        raise DatabaseError("Внутренняя ошибка обновления данных", original_error=e)


async def update_user_password(
    session: AsyncSession,
    user_uid: str,
    new_password: str,
) -> None:
    """
    Обновляет пароль пользователя в базе данных.

    Принимает новый пароль в открытом виде, хеширует его и сохраняет в базе данных.
    В случае успеха сохраняет изменения в базе данных.

    :param session: Асинхронная сессия SQLAlchemy.
    :param user_uid: UID пользователя, для которого обновляется пароль.
    :param new_password: Новый пароль в открытом виде.
    :raises NotFoundError: Если пользователь не найден.
    :raises DatabaseError: Если произошла ошибка при обновлении бд.
    """

    try:
        stmt = select(User).where(User.uid == user_uid)
        result = await session.execute(stmt)
        db_user = result.scalar_one_or_none()

        if db_user is None:
            log.error("Пользователь с uid %s не найден", user_uid)
            raise NotFoundError("Пользователь не найден", resource_type="user")

        db_user.hashed_password = get_password_hash(new_password)
        await session.commit()

    except SQLAlchemyError as e:
        log.error("Ошибка при обновлении пароля пользователя %s: %s", user_uid, str(e))
        await session.rollback()
        raise DatabaseError("Ошибка при обновлении пароля", original_error=e)
