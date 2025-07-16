import datetime as dt
from datetime import timedelta, datetime
from typing import Annotated

from fastapi import HTTPException, status, Request, Depends
from fastapi.security import OAuth2PasswordBearer
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.core.config import settings
from src.app.core.logger import get_logger
from src.app.crud.user import get_user_by_uid, get_user_by_name
from src.app.db import db_helper
from src.app.db.models import User
from src.app.schemas.user import UserResponse
from src.app.services.redis import (
    add_refresh_to_redis,
    revoke_all_refresh_tokens,
    validate_refresh_jwt,
)
from src.app.utils.auth import (
    create_response,
    decode_jwt,
    encode_jwt,
    get_password_hash,
    verify_password,
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login", auto_error=False)
log = get_logger("auth_service")

TOKEN_TYPE_FIELD = "type"
ACCESS_TOKEN_TYPE = "access"
REFRESH_TOKEN_TYPE = "refresh"

CREDENTIAL_EXCEPTION = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail={"message": "Неверные учетные данные"},
    headers={"WWW-Authenticate": "Bearer"},
)


async def get_access_token_from_cookies(request: Request):
    """
    Retrieves the access token from the cookies of an HTTP request.

    This asynchronous function extracts the access token from the cookies
    present in the given HTTP request. If the "access_token" cookie is not
    found, it returns None.

    :param request: The HTTP request object containing the cookies.
    :return: The access token as a string if present, otherwise None.
    """
    token = request.cookies.get("access_token")
    return token


def get_current_token_payload(
    token: str,
) -> dict | None:
    """
    Retrieves the payload of a JWT token.

    This function takes a JWT token as an argument, decodes it, and returns
    the payload as a dictionary. If the token is invalid or has expired, it
    raises an HTTPException with a 401 status code and an appropriate error
    message.

    :param token: The JWT token string to be decoded.
    :return: The decoded payload as a dictionary, or None if the token is
             invalid.
    :raises HTTPException: If the token is invalid or has expired.
    """
    log.debug("Attempting to decode token: %s", token)
    payload: dict | None = decode_jwt(token)
    if payload is None:
        log.error("Failed to decode token: payload is None")
        raise CREDENTIAL_EXCEPTION

    token_type: str | None = payload.get(TOKEN_TYPE_FIELD)
    if token_type is None or token_type != ACCESS_TOKEN_TYPE:
        log.error(
            "No match for token type in token payload: %s",
            payload,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "message": "",
                "details": f"Invalid token type {token_type!r} expected {ACCESS_TOKEN_TYPE!r}",
            },
        )
    uid: str | None = payload.get("sub")
    if uid is None:
        log.error(
            "User uid not found in token payload: %s",
            payload,
        )
        raise CREDENTIAL_EXCEPTION

    return payload


def create_jwt(
    token_type: str,
    token_data: dict,
    expire_minutes: int = settings.auth.access_token_expires,
    expire_timedelta: timedelta | None = None,
) -> str:
    """
    Creates a JWT token with the given payload and expiration duration.

    This function takes the given payload, adds the current time as the "iat"
    claim, and creates a JWT token with the given expiration duration. If the
    `expire_minutes` parameter is provided, it is used as the expiration
    duration. If the `expire_timedelta` parameter is provided, it is used
    instead of the expiration minutes. If there is an HTTP error during
    encoding, it raises an HTTPException with an appropriate status code and
    error message.

    :param token_type: The type of the token to be created.
    :param token_data: The payload to be added to the token.
    :param expire_minutes: The number of minutes before the token expires.
    :param expire_timedelta: The timedelta object representing the expiration
                             time of the token.
    :return: The encoded JWT token as a string.
    :raises HTTPException: If there is an HTTP error during encoding.
    """
    jwt_payload = {
        TOKEN_TYPE_FIELD: token_type,
        "iat": datetime.now(dt.UTC),
    }
    jwt_payload.update(token_data)
    encoded: str = encode_jwt(
        payload=jwt_payload,
        expire_minutes=expire_minutes,
        expire_timedelta=expire_timedelta,
    )
    return encoded


def create_access_jwt(user: UserResponse) -> str:
    """
    Creates an access token for the given user.

    This function takes a user object and creates an access token with the
    user's UID, username, and email as the payload. The token is set to expire
    after the duration specified in the configuration.

    :param user: The user object for which to create the token.
    :return: The encoded JWT token as a string.
    """
    jwt_payload = {
        "sub": user.uid,
        "username": user.username,
        "email": user.email,
    }
    jwt = create_jwt(
        token_type=ACCESS_TOKEN_TYPE,
        token_data=jwt_payload,
        expire_minutes=settings.auth.access_token_expires,
    )

    return jwt


async def create_refresh_jwt(
    user: UserResponse,
) -> str:
    """
    Creates a refresh token for the given user.

    This function takes a user object and creates a refresh token with the
    user's UID as the payload. The token is set to expire after the duration
    specified in the configuration. The function also stores the token in Redis,
    ensuring that no more than four tokens exist for the user by deleting the
    oldest token if necessary.

    :param user: The user object for which to create the token.
    :return: The encoded JWT token as a string.
    :raises HTTPException: If there is an HTTP error during encoding or storing
                           the token in Redis.
    """
    jwt_payload = {
        "sub": user.uid,
    }
    jwt_expires = timedelta(days=settings.auth.refresh_token_expires)

    jwt = create_jwt(
        token_type=REFRESH_TOKEN_TYPE,
        token_data=jwt_payload,
        expire_timedelta=jwt_expires,
    )
    await add_refresh_to_redis(
        uid=user.uid,
        jwt=jwt,
        exp=jwt_expires,
    )

    return jwt


async def update_password(
    user: UserResponse,
    session: AsyncSession,
    new_password: str,
):
    """
    Updates the password for the given user.

    Given a user object and a new password, updates the user's password in the
    database. The function first queries the database for the user, then
    updates the user's password with the new password (hashed with a secure
    hashing algorithm). The function then commits the changes and revokes all
    refresh tokens for the user. Finally, the function returns a response
    containing a new access and refresh token for the user.

    :param user: The user object whose password is to be updated.
    :param session: The database session to use for the query.
    :param new_password: The new password to set for the user.
    :return: A response containing the new access and refresh tokens.
    :raises HTTPException: If the user is not found in the database.
    """
    stmt = select(User).where(User.uid == user.uid)
    result = await session.execute(stmt)
    db_user = result.scalar_one_or_none()
    if db_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "message": "Пользователь не найден",
            },
        )
    db_user.hashed_password = get_password_hash(new_password)

    await session.commit()
    await revoke_all_refresh_tokens(user.uid)

    return await add_tokens_to_response(user)


async def add_tokens_to_response(user: UserResponse):
    """
    Adds an access token and refresh token to a response for the given user.

    This function creates an access token and a refresh token for the given user
    object and adds them to a response object. It returns the response object.

    :param user: The user object for which to add tokens to the response.
    :return: The response object with the access token and refresh token added.
    """
    access_jwt = create_access_jwt(user)
    refresh_jwt = await create_refresh_jwt(user)

    response = create_response(
        access_token=access_jwt,
        refresh_token=refresh_jwt,
    )

    return response


async def get_current_auth_user(
    token: Annotated[str, Depends(get_access_token_from_cookies)],
    session: Annotated[AsyncSession, Depends(db_helper.session_getter)],
) -> UserResponse | None:
    """
    Authenticates a user given a JWT token and returns the user object.

    If the token is invalid, has expired, or the user is not found, raises an
    HTTPException with a 401 status code.

    :param token: The JWT token to authenticate with.
    :param session: The database session to use for the query.
    :return: The authenticated user object, or None if authentication fails.
    """
    if token is None:
        return None
    try:
        payload: dict = get_current_token_payload(token)
        uid: str | None = payload.get("sub")
        log.debug(
            "Looking for user with uid: %s",
            uid,
        )
        user = await get_user_by_uid(session, uid)
    except HTTPException as e:
        raise e
    else:
        if user is None:
            log.error(
                "User not found for uid: %s",
                uid,
            )
            raise CREDENTIAL_EXCEPTION

        return user


async def get_current_auth_user_for_refresh(
    token: str,
    session: AsyncSession,
    redis: Redis,
) -> UserResponse:
    """
    Authenticates a user given a refresh token and returns the user object.

    If the token is invalid, has expired, or the user is not found, raises an
    HTTPException with a 401 status code.

    :param token: The refresh token to authenticate with.
    :param session: The database session to use for the query.
    :param redis: The Redis client to use for the query.
    :return: The authenticated user object.
    """
    payload = decode_jwt(token)
    if payload is None:
        log.error("Failed to decode refresh token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "message": "Ошибка аутентификации. Пожалуйста, войдите заново",
                "details": "Failed to decode refresh token",
            },
        )

    uid: str | None = payload.get("sub")
    if uid is None:
        log.error("User id not found in refresh token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "message": "Ошибка аутентификации. Пожалуйста, войдите заново",
                "details": "User id not found in refresh token",
            },
        )
    if not await validate_refresh_jwt(uid, token, redis):
        log.error("Refresh token is invalid or has expired")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "message": "Ошибка аутентификации. Пожалуйста, войдите заново",
                "details": "Refresh token is invalid or has expired",
            },
        )
    user = await get_user_by_uid(session, uid)

    return user


async def authenticate_user(
    session: AsyncSession,
    username: str,
    password: str,
) -> UserResponse | None:
    """
    Authenticates a user by validating their username and password.

    This function retrieves a user from the database using the provided
    username and verifies the provided password against the stored
    hashed password. If the password is incorrect, it raises an HTTPException
    with a 401 status code.

    :param session: The current database session.
    :param username: The username of the user to authenticate.
    :param password: The password of the user to authenticate.
    :return: A `UserResponse` object containing the authenticated user's data,
             or None if the authentication fails.
    :raises HTTPException: If the password is incorrect.
    """
    user = await get_user_by_name(session, username)

    if not verify_password(password, user.hashed_password):
        log.error(
            "Invalid password for user: %s",
            username,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "message": "Введён неверный пароль"
            },
        )

    return UserResponse.model_validate(user)
