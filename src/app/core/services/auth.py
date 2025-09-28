from typing import Annotated, Any

from fastapi import Depends, HTTPException, Request, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.core import db_helper
from src.app.core.constants import CREDENTIAL_EXCEPTION
from src.app.core.logger import get_logger
from src.app.core.services.jwt_service import (
    ACCESS_TOKEN_TYPE,
    TOKEN_TYPE_FIELD,
    decode_jwt,
)
from src.app.core.services.redis import validate_refresh_jwt
from src.app.core.utils.auth import verify_password
from src.app.crud.user import get_user_by_name, get_user_by_uid
from src.app.schemas.user import UserPublic

log = get_logger("auth_service")


async def get_access_token_from_cookies(request: Request) -> str | None:
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


def get_current_access_token_payload(
    token: str,
) -> dict[str, Any]:
    """
    Retrieves the payload of the current access token.

    This function takes the given access token and attempts to decode it
    using the decode_jwt function. If the decoding fails, a 401 HTTP
    exception is raised with an appropriate error message. If the
    "type" field in the payload is not "access", a 401 HTTP exception is
    also raised.

    :param token: The access token to be decoded.
    :return: The payload of the access token as a dictionary.
    :raises HTTPException: If the decoding fails or the "type" field is
                           not "access".
    """

    log.debug("Attempting to decode token: %s", token)

    payload: dict[str, Any] | None = decode_jwt(token)
    if payload is None:
        log.error("Failed to decode token: payload is None")
        raise CREDENTIAL_EXCEPTION

    token_type: str | None = payload.get(TOKEN_TYPE_FIELD)
    if token_type is None or token_type != ACCESS_TOKEN_TYPE:
        log.error(
            "No match for token type in token payload: %s",
            payload,
        )
        raise CREDENTIAL_EXCEPTION

    return payload


async def get_current_auth_user(
    token: Annotated[str, Depends(get_access_token_from_cookies)],
    session: Annotated[AsyncSession, Depends(db_helper.session_getter)],
) -> UserPublic | None:
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

    payload: dict = get_current_access_token_payload(token)
    uid: str | None = payload.get("sub")
    if uid is None:
        log.error("Ошибка получения uid из payload")
        raise CREDENTIAL_EXCEPTION

    try:
        # используем кешированную версию get_user_by_uid
        user = await get_user_by_uid(session, uid)
        return user

    except Exception as e:
        log.error("Ошибка при получении пользователя: %s", str(e))
        raise CREDENTIAL_EXCEPTION


async def get_current_auth_user_for_refresh(
    token: str,
    session: AsyncSession,
    redis: Redis,
) -> UserPublic:
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
        log.error("Ошибка декодирования refresh токена")
        raise CREDENTIAL_EXCEPTION

    uid: str | None = payload.get("sub")
    if uid is None:
        log.error("id пользователя не найден в refresh токене")
        raise CREDENTIAL_EXCEPTION

    if not await validate_refresh_jwt(uid, token, redis):
        log.error("refresh токен невалиден или устарел")
        raise CREDENTIAL_EXCEPTION

    user = await get_user_by_uid(session, uid)

    return user


async def authenticate_user(
    session: AsyncSession,
    username: str,
    password: str,
) -> UserPublic | None:
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
            "Неверный пароль для пользователя: %s",
            username,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"message": "Введён неверный пароль"},
        )

    return UserPublic.model_validate(user)
