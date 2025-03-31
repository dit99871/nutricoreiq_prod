from typing import Annotated

from fastapi import Depends, HTTPException, status
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
    REFRESH_TOKEN_TYPE,
    TOKEN_TYPE_FIELD,
)
from utils.auth import verify_password
from crud.user import get_user_by_name

log = get_logger("user_service")


async def _get_user_from_token(
    token: str,
    db: AsyncSession,
    expected_token_type: str,
) -> UserResponse | None:
    try:
        payload: dict = get_current_token_payload(token)
        name: str | None = payload.get("sub")
        token_type = payload.get(TOKEN_TYPE_FIELD)
        # add check jti in blacklist
        log.debug("Looking for user with name: %s", name)
        user = await get_user_by_name(db, name)
    except HTTPException as e:
        raise e
    else:
        if user is None:
            log.error("User not found for name: %s", name)
            raise CREDENTIAL_EXCEPTION
        if token_type != expected_token_type:
            log.error(
                "Invalid token type. Expected %s, got %s",
                expected_token_type,
                token_type,
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token type. Expected {expected_token_type!r}, got {token_type!r}",
            )

        log.info("User authenticated successfully: %s", name)
        return UserResponse.model_validate(user)


async def get_current_auth_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(db_helper.session_getter)],
) -> UserResponse | None:
    if token is None:
        return None
    try:
        return await _get_user_from_token(token, db, ACCESS_TOKEN_TYPE)
    except HTTPException as e:
        raise e


async def get_current_auth_user_for_refresh(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(db_helper.session_getter)],
) -> UserResponse:
    try:
        return await _get_user_from_token(token, db, REFRESH_TOKEN_TYPE)
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
