from fastapi import status
from fastapi.exceptions import HTTPException
from pydantic import EmailStr
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from src.app.core.logger import get_logger
from src.app.models import User
from src.app.schemas.user import UserCreate, UserResponse
from src.app.utils.auth import get_password_hash

log = get_logger("user_crud")


async def _get_user_by_filter(
    session: AsyncSession,
    filter_condition,
) -> UserResponse | None:
    """
    Helper function to get a user from the database using a filter condition.

    Given a `filter_condition` argument, constructs a SQLAlchemy query to fetch a user
    from the database. The query will only return active users.

    On success, returns a `UserResponse` object containing the user's data. If the user
    is not found, returns `None`.

    If a database error occurs, raises an `HTTPException` with a 404 status code and
    a detail string containing the error message. If an unexpected error occurs,
    raises an `HTTPException` with a 500 status code and a detail string containing the
    error message.

    :param session: The current database session.
    :param filter_condition: The filter condition to use in the query.
    :return: A `UserResponse` object containing the user's data, or `None` if the user
        is not found.
    :raises HTTPException: If a database error or unexpected error occurs.
    """
    try:
        stmt = select(User).filter(filter_condition, User.is_active == True)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        return UserResponse.model_validate(user) if user else None

    except SQLAlchemyError as e:
        log.error(
            "Database error getting user: %s",
            str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "message": "Внутренняя ошибка сервера",
            },
        )


async def get_user_by_uid(
    session: AsyncSession,
    uid: str,
) -> UserResponse:
    """
    Fetches a user from the database by their user ID (UID).

    Given a `session` and a `uid`, constructs a SQLAlchemy query to fetch a user
    from the database. The query will only return active users.

    On success, returns a `UserResponse` object containing the user's data. If the user
    is not found, raises an `HTTPException` with a 404 status code and a detail string
    containing the error message. If an unexpected error occurs, raises an
    `HTTPException` with a 500 status code and a detail string containing the error
    message.

    :param session: The current database session.
    :param uid: The UID of the user to fetch.
    :return: A `UserResponse` object containing the user's data, or raises an
        `HTTPException` if the user is not found.
    :raises HTTPException: If the user is not found or an unexpected error occurs.
    """
    user = await _get_user_by_filter(session, User.uid == uid)
    if user is None:
        log.error("User not found in db by uid")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "message": "Пользователь не найден",
            },
        )
    return user


async def get_user_by_email(
    session: AsyncSession,
    email: EmailStr,
) -> UserResponse | None:
    """
    Fetches a user from the database by their email address.

    Given a `session` and an `email`, constructs a SQLAlchemy query to fetch a user
    from the database. The query will only return active users.

    On success, returns a `UserResponse` object containing the user's data. If the user
    is not found, returns `None`.

    :param session: The current database session.
    :param email: The email address of the user to fetch.
    :return: A `UserResponse` object containing the user's data, or `None` if the user
        is not found.
    """
    user = await _get_user_by_filter(session, User.email == email)

    return user


async def get_user_by_name(
    session: AsyncSession,
    user_name: str,
) -> UserResponse:
    """
    Fetches a user from the database by their username.

    Constructs a SQLAlchemy query to fetch an active user from the database
    using the provided `user_name`. If the user is found, returns a `UserResponse`
    object containing the user's data. If the user is not found, raises an
    `HTTPException` with a 404 status code and an appropriate error message.

    :param session: The current database session.
    :param user_name: The username of the user to fetch.
    :return: A `UserResponse` object containing the user's data, or raises an
        `HTTPException` if the user is not found.
    :raises HTTPException: If the user is not found in the database.
    """
    user = await _get_user_by_filter(session, User.username == user_name)
    if user is None:
        log.error("User not found in db by name")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": "Пользователь с таким именем не найден"},
        )
    return user


async def create_user(
    session: AsyncSession,
    user_in: UserCreate,
) -> UserCreate | None:
    """
    Creates a new user in the database.

    Given a `UserCreate` object as input, this function creates a new user in the
    database. The function first hashes the password using a secure password hashing
    algorithm, then creates a new `User` object with the input data and the hashed
    password. The object is then added to the database and committed.

    On success, returns the `UserCreate` object that was passed in. If the user is not
    found, raises an `HTTPException` with a 500 status code and a detail string
    containing the error message. If an unexpected error occurs, raises an
    `HTTPException` with a 500 status code and a detail string containing the error
    message.

    :param session: The current database session.
    :param user_in: The user data to create.
    :return: The created user, or `None` if an error occurs.
    :raises HTTPException: If an error occurs during the creation of the user.
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

        return user_in

    except SQLAlchemyError as e:
        log.error(
            "Database error creating user_in with email %s: %s",
            user_in.email,
            str(e),
        )
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "Ошибка при создании пользователя",
            },
        )


async def choose_subscribe_status(
    user: UserResponse,
    session: AsyncSession,
    condition: bool,
):
    """
    Updates the subscription status for the given user.

    :param user: The user object (Pydantic UserResponse) whose subscription status is to be updated.
    :param session: The current database session.
    :param condition: A boolean value indicating the desired subscription status.
    :return: None
    :raises HTTPException: If the user is not found or the database operation fails.
    """
    stmt = select(User).filter(User.uid == user.uid, User.is_active == True)
    result = await session.execute(stmt)
    target_user = result.scalar_one_or_none()

    if not target_user:
        log.error(
            "Пользователь с uid %s не найден или неактивен",
            user.uid,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": "Пользователь не найден"},
        )
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
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "Внутренняя ошибка обновления данных",
            },
        )
