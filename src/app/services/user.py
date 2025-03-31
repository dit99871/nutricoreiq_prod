from typing import Annotated

from fastapi import Depends, HTTPException, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from core.logger import get_logger
from db import db_helper
from db.models import User
from schemas.user import UserResponse
from services.auth import (
    ACCESS_TOKEN_TYPE,
    CREDENTIAL_EXCEPTION,
    get_current_token_payload,
    oauth2_scheme,
    TOKEN_TYPE_FIELD,
)
from utils.auth import verify_password, decode_jwt
from crud.user import get_user_by_name, get_user_by_id
from utils.redis import validate_refresh_jwt

log = get_logger("user_service")


async def get_current_auth_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(db_helper.session_getter)],
) -> UserResponse | None:
    if token is None:
        return None
    try:
        payload: dict = get_current_token_payload(token)
        user_id: int | None = payload.get("sub")
        log.debug("Looking for user with user_id: %s", user_id)
        user = await get_user_by_id(db, user_id)
    except HTTPException as e:
        raise e
    else:
        if user is None:
            log.error("User not found for user_id: %s", user_id)
            raise CREDENTIAL_EXCEPTION

        log.info("User authenticated successfully: %s", user_id)
        return UserResponse.model_validate(user)


async def get_current_auth_user_for_refresh(
    token: str,
    session: AsyncSession,
    redis: Redis,
) -> UserResponse:
    try:
        payload = decode_jwt(token)
        if payload is None:
            log.error("Failed to decode refresh token")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Failed to decode refresh token",
            )

        user_id: int | None = payload.get("sub")
        if user_id is None:
            log.error("User id not found in refresh token")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User id not found in refresh token",
            )
        if not await validate_refresh_jwt(user_id, token, redis):
            log.error("Refresh token is invalid or has expired")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token is invalid or has expired",
            )
        user = await get_user_by_id(session, user_id)
        return user
    except HTTPException as e:
        raise e


async def authenticate_user(
    db: Annotated[AsyncSession, Depends(db_helper.session_getter)],
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
        db (Annotated[AsyncSession, Depends]): The async database session dependency.
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
        user = await get_user_by_name(db, username)
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
