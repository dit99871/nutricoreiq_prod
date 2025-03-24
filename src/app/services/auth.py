import datetime as dt
from datetime import timedelta, datetime
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.logger import get_logger
from db import db_helper
from models.user import User
from utils import decode_jwt, encode_jwt, verify_password
from crud.user import get_user_by_name
from schemas.user import UserSchema

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login")
log = get_logger(__name__)

TOKEN_TYPE_FIELD = "type"
ACCESS_TOKEN_TYPE = "access"
REFRESH_TOKEN_TYPE = "refresh"

CREDENTIAL_EXCEPTION = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_auth_payload(token: str) -> str | None:
    """
    Decodes the given JWT token to extract the username.

    This function attempts to decode the provided JWT token to extract the
    username ('sub' field) from its payload. If decoding fails or the 'sub'
    field is not present, it raises an HTTP 401 Unauthorized exception.

    Args:
        token (str): The JWT token to be decoded.

    Returns:
        str | None: The username extracted from the token payload.

    Raises:
        HTTPException: If the token cannot be decoded or the 'sub' field is missing.
    """
    log.debug("Attempting to decode token: %s", token)

    payload: dict | None = decode_jwt(token)
    if payload is None:
        log.error("Failed to decode token: payload is None")
        raise CREDENTIAL_EXCEPTION

    token_type: str | None = payload.get(TOKEN_TYPE_FIELD)
    if token_type is None:
        log.error("Token type not found in token payload: %s", payload)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token type {token_type!r} expected {ACCESS_TOKEN_TYPE!r}",
        )
    name: str | None = payload.get("sub")
    if name is None:
        log.error("Name not found in token payload: %s", payload)
        raise CREDENTIAL_EXCEPTION

    return name


async def get_current_auth_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(db_helper.session_getter)],
) -> User:
    """
    Retrieves the user associated with the given authentication token.

    This function attempts to retrieve the user associated with the given
    authentication token. If the token is invalid or the user is not found,
    an HTTP 401 Unauthorized exception is raised.

    Args:
        token (Annotated[str, Depends]): The authentication token to be decoded.
        db (Annotated[AsyncSession, Depends]): The async database session dependency.

    Returns:
        UserRead: The user object associated with the given token.

    Raises:
        HTTPException: If the token is invalid or the user is not found.
    """
    try:
        name: str | None = get_current_auth_payload(token)

        log.debug("Looking for user with name: %s", name)
        user = await get_user_by_name(db, name)
    except HTTPException as e:
        raise e
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


def create_jwt(
    token_type: str,
    token_data: dict,
    expire_minutes: int = settings.auth.access_token_expires,
    expire_timedelta: timedelta | None = None,
) -> str:
    """
    Generates a JSON Web Token (JWT) with the specified token type and data.

    This function creates a JWT with a payload containing the specified token
    type and additional token data. The token is encoded using a private key,
    and it includes an issued-at timestamp. The token's expiration can be set
    either by specifying the number of minutes it should be valid or by providing
    a specific timedelta.

    Args:
        token_type (str): The type of the token (e.g., access, refresh).
        token_data (dict): Additional data to include in the token's payload.
        expire_minutes (int, optional): The number of minutes until the token expires.
            Defaults to the value specified in settings.auth.access_token_expires.
        expire_timedelta (timedelta | None, optional): A specific timedelta for the
            token's expiration, which takes precedence over expire_minutes if provided.

    Returns:
        str: The encoded JWT as a string.
    """
    jwt_payload = {
        TOKEN_TYPE_FIELD: token_type,
        "iat": datetime.now(dt.UTC),
    }
    jwt_payload.update(token_data)
    try:
        encoded = encode_jwt(
            payload=jwt_payload,
            expire_minutes=expire_minutes,
            expire_timedelta=expire_timedelta,
        )
        return encoded
    except HTTPException as e:
        raise e


def create_access_token(user: User) -> str:
    """
    Creates a JWT token based on the provided user.

    This function creates a JWT token based on the user's username and email,
    with a payload containing the user's username and email. The token is signed
    with the private key specified in the `settings.auth.private_key_path` environment
    variable, and will expire after the amount of time specified in the
    `settings.auth.access_token_expire` environment variable.

    Args:
        user (User): The user object containing the username and email.

    Returns:
        str: The JWT token.
    """
    jwt_payload = {
        "sub": user.username,
        "username": user.username,
        "email": user.email,
    }
    try:
        jwt = create_jwt(
            token_type=ACCESS_TOKEN_TYPE,
            token_data=jwt_payload,
            expire_minutes=settings.auth.access_token_expires,
        )
        return jwt
    except HTTPException as e:
        raise e


def create_refresh_token(user: User) -> str:
    """
    Creates a refresh JWT token for the provided user.

    This function generates a refresh token with a payload containing the user's
    username. The token is signed using the private key and is configured to
    expire after the number of days specified in the `settings.auth.refresh_token_expire`
    configuration.

    Args:
        user (User): The user object for whom the refresh token is being created.

    Returns:
        str: The encoded refresh JWT token as a string.
    """
    jwt_payload = {
        "sub": user.username,
    }
    try:
        jwt = create_jwt(
            token_type=REFRESH_TOKEN_TYPE,
            token_data=jwt_payload,
            expire_timedelta=timedelta(days=settings.auth.refresh_token_expires),
        )
        return jwt
    except HTTPException as e:
        raise e
