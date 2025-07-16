import datetime as dt
import uuid
from typing import Any

import bcrypt
from fastapi import status
from fastapi.exceptions import HTTPException
from fastapi.responses import ORJSONResponse
from jose import jwt, JWTError, ExpiredSignatureError

from src.app.core.config import settings
from src.app.core.logger import get_logger

log = get_logger("auth_utils")


def get_password_hash(password: str) -> bytes:
    """
    Returns bytes object of hashed password.

    Hashes given password with random salt and returns it as bytes.

    :param password: Password to be hashed.
    :return: Hashed password as bytes.
    """
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode(), salt)


def verify_password(
    password: str,
    hashed_password: bytes,
) -> bool:
    """
    Verifies if given password matches given hashed password.

    Compares given password with given hashed password using
    `bcrypt.checkpw` and returns `True` if they match and `False` otherwise.

    :param password: Password to be verified.
    :param hashed_password: Hashed password to compare with.
    :return: `True` if password matches, `False` otherwise.
    """
    return bcrypt.checkpw(
        password=password.encode(),
        hashed_password=hashed_password,
    )


def decode_jwt(token: str) -> dict[str, Any] | None:
    """
    Decodes a JWT token using the public key.

    This function attempts to decode a given JWT token using the public key
    specified in the configuration. If successful, it returns the decoded
    payload as a dictionary. If the public key file is not found, the token
    has expired, or there is a JWT error, it raises an HTTPException with
    an appropriate status code and error message.

    :param token: The JWT token to be decoded.
    :return: The decoded payload as a dictionary, or None if decoding fails.
    :raises HTTPException: If the public key file is not found, the token
                           has expired, or a JWT error occurs during decoding.
    """
    if token is None:
        return None
    try:
        decoded = jwt.decode(
            token,
            settings.auth.public_key_path.read_text(),
            algorithms=settings.auth.algorithm,
        )
        return decoded
    except FileNotFoundError as e:
        log.error("File with public key not found: %s", e)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File with public key not found {str(e)}",
        )
    except ExpiredSignatureError as e:
        log.error("Token has expired: %s", e)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token has expired: {str(e)}.",
        )
    except JWTError as e:
        log.error("Invalid token: %s", e)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
        )


def encode_jwt(
    payload: dict,
    algorithm: str = settings.auth.algorithm,
    expire_minutes: int = settings.auth.access_token_expires,
    expire_timedelta: dt.timedelta | None = None,
) -> str:
    """
    Encodes a JWT token from the given payload and configuration.

    This function encodes a JWT token using the private key specified in the
    configuration and the given payload. If the private key file is not found,
    a JWT error occurs during encoding, or the `expire_minutes` parameter is
    invalid, it raises an HTTPException with an appropriate status code and
    error message.

    :param payload: The payload to be encoded into the JWT token.
    :param algorithm: The algorithm to use for encoding the token, defaults to
                      the algorithm specified in the configuration.
    :param expire_minutes: The number of minutes before the token expires,
                           defaults to the expiration time specified in the
                           configuration.
    :param expire_timedelta: The timedelta object representing the expiration
                             time of the token, overrides the `expire_minutes`
                             parameter if provided.
    :return: The encoded JWT token as a string.
    :raises HTTPException: If the private key file is not found, the token
                           has expired, or a JWT error occurs during encoding.
    """
    try:
        private_key = settings.auth.private_key_path.read_text()

    except FileNotFoundError as e:
        log.error("File with private key not found: %s", e)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "message": "Ошибка авторизации",
                "details": f"File with private key not found: {str(e)}.",
            },
        )

    to_encode = payload.copy()
    now = dt.datetime.now(dt.UTC)

    expire = (
        now + expire_timedelta
        if expire_timedelta
        else now + dt.timedelta(minutes=expire_minutes)
    )
    to_encode.update(
        exp=expire,
        iat=now,
        jti=str(uuid.uuid4()),
    )
    try:
        encoded = jwt.encode(
            to_encode,
            private_key,
            algorithm=algorithm,
        )
        return encoded
    except JWTError as e:
        log.error("JWT error encoding token: %s", e)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "message": "Ошибка авторизации",
                "details": f"JWT error encoding token: {str(e)}",
            },
        )


def create_response(
    access_token: str,
    refresh_token: str,
) -> ORJSONResponse:
    """
    Creates a response with the given access token and refresh token.

    This function creates an instance of `ORJSONResponse` with the given access
    token and refresh token. It sets the status code to HTTP 200 OK, the
    Cache-Control header to "no-store", the Pragma header to "no-cache", and
    the Content-Type header to "application/json". It sets the "access_token"
    key in the response body to the given access token, and the "token_type"
    key to "bearer". It also sets the Set-Cookie header with the given refresh
    token, the "refresh_token" key in the cookie, the "httponly" and "secure"
    flags set to True, and the "sameSite" flag set to "lax". The "domain" and
    "path" parameters are not set by default but can be set if needed.

    :param access_token: The access token to be set in the response.
    :param refresh_token: The refresh token to be set in the response.
    :return: The `ORJSONResponse` instance with the given access token and
             refresh token.
    """
    response = ORJSONResponse(
        status_code=status.HTTP_200_OK,
        headers={
            "Cache-Control": "no-store",
            "Pragma": "no-cache",
        },
        content={
            "message": "Password changed successfully",
        },
    )

    expires_refresh_token = dt.datetime.now(dt.UTC) + dt.timedelta(
        days=settings.auth.refresh_token_expires
    )
    expires_access_token = dt.datetime.now(dt.UTC) + dt.timedelta(
        minutes=settings.auth.access_token_expires
    )

    def _set_cookies(
        key: str,
        value: str,
        expires: dt.datetime,
        response_in=response,
    ):
        response_in.set_cookie(
            key=key,
            value=value,
            httponly=True,
            secure=True,  # switch on production
            samesite="lax",  # than use csrf tokens else "strict"
            expires=expires,
        )

    _set_cookies(
        key="access_token",
        value=access_token,
        expires=expires_access_token,
    )
    _set_cookies(
        key="refresh_token",
        value=refresh_token,
        expires=expires_refresh_token,
    )

    return response
