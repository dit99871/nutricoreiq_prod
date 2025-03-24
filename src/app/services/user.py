from typing import Annotated

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.logger import get_logger
from db import db_helper
from db.models import User
from services.auth import (
    CREDENTIAL_EXCEPTION,
    get_current_auth_payload,
    oauth2_scheme,
)
from utils.auth import verify_password
from crud.user import get_user_by_name

log = get_logger(__name__)


async def get_current_auth_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(db_helper.session_getter)],
) -> User:
    try:
        payload: dict = get_current_auth_payload(token)
        name: str | None = payload.get("sub")
        log.debug("Looking for user with name: %s", name)
        user = await get_user_by_name(db, name)
    except HTTPException as e:
        raise e
    else:
        if user is None:
            log.error("User not found for name: %s", name)
            raise CREDENTIAL_EXCEPTION

        log.info("User authenticated successfully: %s", name)
        return user


async def authenticate_user(
    db: Annotated[AsyncSession, Depends(db_helper.session_getter)],
    username: str,
    password: str,
) -> User | None:
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
            log.error("User not found: %s", username)
            raise unauthed_exc

        log.debug("User found: %s. Verifying password.", username)
        if not verify_password(password, user.hashed_password):
            log.error("Invalid password for user: %s", username)
            raise unauthed_exc

        log.info("User authenticated successfully: %s", username)
        return user
