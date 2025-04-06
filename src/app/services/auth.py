import datetime as dt
from datetime import timedelta, datetime

from fastapi import HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer

from core.config import settings
from core.logger import get_logger
from db.models import User
from schemas.user import UserResponse
from services.redis import (
    add_refresh_to_redis,
    revoke_all_refresh_tokens,
)
from utils.auth import decode_jwt, encode_jwt, create_response, add_tokens_to_response

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login", auto_error=False)
log = get_logger("auth_service")

TOKEN_TYPE_FIELD = "type"
ACCESS_TOKEN_TYPE = "access"
REFRESH_TOKEN_TYPE = "refresh"

CREDENTIAL_EXCEPTION = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


async def get_token_from_cookies(request: Request):
    token = request.cookies.get("access_token")
    return token


def get_current_token_payload(
    token: str,
) -> dict | None:
    log.debug("Attempting to decode token: %s", token)
    payload: dict | None = decode_jwt(token)
    if payload is None:
        log.error("Failed to decode token: payload is None")
        raise CREDENTIAL_EXCEPTION

    token_type: str | None = payload.get(TOKEN_TYPE_FIELD)
    if token_type is None or token_type != ACCESS_TOKEN_TYPE:
        log.error("No match for token type in token payload: %s", payload)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token type {token_type!r} expected {ACCESS_TOKEN_TYPE!r}",
        )
    uid: str | None = payload.get("sub")
    if uid is None:
        log.error("User uid not found in token payload: %s", payload)
        raise CREDENTIAL_EXCEPTION

    return payload


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
        encoded: str = encode_jwt(
            payload=jwt_payload,
            expire_minutes=expire_minutes,
            expire_timedelta=expire_timedelta,
        )
        return encoded
    except HTTPException as e:
        raise e


def create_access_jwt(user: UserResponse) -> str:
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
        "sub": user.uid,
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


async def create_refresh_jwt(
    user: UserResponse,
) -> str:
    jwt_payload = {
        "sub": user.uid,
    }
    jwt_expires = timedelta(days=settings.auth.refresh_token_expires)
    try:
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

    except HTTPException as e:
        raise e

    except Exception as e:
        log.exception("Unexpected error creating refresh token: %s", e)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )


async def update_password(user: UserResponse):
    await revoke_all_refresh_tokens(user.uid)

    return await add_tokens_to_response(user)
