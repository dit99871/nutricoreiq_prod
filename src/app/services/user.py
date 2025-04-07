from typing import Annotated

from fastapi import Depends, HTTPException, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from core.logger import get_logger
from db import db_helper
from db.models import User
from schemas.user import UserResponse
from services.auth import (
    CREDENTIAL_EXCEPTION,
    get_current_token_payload,
    get_access_token_from_cookies,
)
from utils.auth import verify_password, decode_jwt
from crud.user import get_user_by_name, get_user_by_uid
from services.redis import validate_refresh_jwt

log = get_logger("user_service")


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
        log.debug("Looking for user with uid: %s", uid)
        user = await get_user_by_uid(session, uid)
    except HTTPException as e:
        raise e
    else:
        if user is None:
            log.error("User not found for uid: %s", uid)
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
    try:
        payload = decode_jwt(token)
        if payload is None:
            log.error("Failed to decode refresh token")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Failed to decode refresh token",
            )

        uid: str | None = payload.get("sub")
        if uid is None:
            log.error("User id not found in refresh token")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User id not found in refresh token",
            )
        if not await validate_refresh_jwt(uid, token, redis):
            log.error("Refresh token is invalid or has expired")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token is invalid or has expired",
            )
        user = await get_user_by_uid(session, uid)
        return user
    except HTTPException as e:
        raise e


async def authenticate_user(
    session: AsyncSession,
    username: str,
    password: str,
) -> UserResponse | None:
    """
    Authenticates a user with the given username and password.

    This function attempts to authenticate a user by checking if the provided
    username exists and if the password matches the stored hashed password.
    If the user is found and the password is correct, the user object is returned.
    Otherwise, an HTTP 401 Unauthorized exception is raised.

    Args:
        session (Annotated[AsyncSession, Depends]): The async database session dependency.
        username (str): The username of the user to authenticate.
        password (str): The password of the user to authenticate.

    Returns:
        User | None: The authenticated user object, or None if authentication fails.

    Raises:
        HTTPException: If the user is not found or the password is incorrect.
    """
    log.debug("Attempting to authenticate user: %s", username)
    unauthed_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid email or password",
    )
    try:
        user = await get_user_by_name(session, username)
    except HTTPException as e:
        raise e
    else:
        if user is None:
            log.error("User not found in db for authentication: %s", username)
            raise unauthed_exc

        log.debug("User found: %s. Verifying password.", username)
        if not verify_password(password, user.hashed_password):
            log.error("Invalid password for user: %s", username)
            raise unauthed_exc

        log.info("User authenticated successfully: %s", username)
        return UserResponse.model_validate(user)
