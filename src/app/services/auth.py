import datetime as dt
from datetime import timedelta, datetime

from fastapi import HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer

from core.config import settings
from core.logger import get_logger
from schemas.user import UserResponse
from services.redis import (
    add_refresh_to_redis,
    revoke_all_refresh_tokens,
)
from utils.auth import decode_jwt, encode_jwt, create_response

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
    Creates an access token for the given user.

    This function takes a user object and creates an access token with the
    user's UID, username, and email as the payload. The token is set to expire
    after the duration specified in the configuration.

    :param user: The user object for which to create the token.
    :return: The encoded JWT token as a string.
    :raises HTTPException: If there is an HTTP error during encoding.
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
    """
    Creates a refresh token for the given user.

    This function takes a user object and creates a refresh token with the
    user's UID as the payload. The token is set to expire after the duration
    specified in the configuration. The function adds the token to Redis
    and returns the encoded JWT token as a string.

    :param user: The user object for which to create the token.
    :return: The encoded JWT token as a string.
    :raises HTTPException: If there is an HTTP error during encoding or adding
                           to Redis.
    """
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
    """
    Revoke all refresh tokens for the user and generate new tokens.

    This function is used when the user's password has been changed. It revokes all
    refresh tokens for the user and generates new tokens. The function returns the
    new tokens as part of a response.

    :param user: The user object for which to revoke all refresh tokens and
                 generate new tokens.
    :return: A response containing the new access and refresh tokens.
    """
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
