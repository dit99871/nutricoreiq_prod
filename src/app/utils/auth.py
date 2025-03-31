import uuid
import datetime as dt
from datetime import datetime, timedelta

import bcrypt
from fastapi import status
from fastapi.exceptions import HTTPException
from fastapi.responses import ORJSONResponse
from jose import jwt, JWTError, ExpiredSignatureError
from redis.asyncio import Redis

from core.config import settings
from core.logger import get_logger
from utils.security import generate_hash_token

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


def decode_jwt(token: str) -> dict | None:
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
        decoded: dict = jwt.decode(
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
    private_key: str = settings.auth.private_key_path.read_text(),
    algorithm: str = settings.auth.algorithm,
    expire_minutes: int = settings.auth.access_token_expires,
    expire_timedelta: timedelta | None = None,
) -> str:
    """
    Encodes a given payload as a JWT token using the private key.

    This function creates a JWT token from a given payload using the private key
    specified in the configuration. It adds the current time as the "iat" claim,
    a unique identifier as the "jti" claim, and an expiration time based on the
    given `expire_minutes` parameter or the `expire_timedelta` parameter. If the
    private key file is not found, a JWT error occurs, or there is an HTTP error
    during encoding, it raises an HTTPException with an appropriate status code
    and error message.

    :param payload: The payload to be encoded as a JWT token.
    :param private_key: The private key to be used for encoding.
    :param algorithm: The algorithm to be used for encoding.
    :param expire_minutes: The number of minutes before the token expires.
    :param expire_timedelta: The timedelta object representing the expiration
                             time of the token.
    :raises HTTPException: If the private key file is not found, a JWT error
                           occurs during encoding, or an HTTP error occurs.
    :return: The encoded JWT token as a string.
    """
    to_encode = payload.copy()
    now = datetime.now(dt.UTC)

    expire = (
        now + expire_timedelta
        if expire_timedelta
        else now + timedelta(minutes=expire_minutes)
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
    except FileNotFoundError as e:
        log.error("File with private key not found: %s", e)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File with private key not found: {str(e)}.",
        )
    except JWTError as e:
        log.error("JWT error encoding token: %s", e)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"JWT error encoding token: {str(e)}",
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
            "access_token": access_token,
            "token_type": "bearer",
        },
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=False,  # switch on production
        samesite="lax",
        # Можно добавить domain, path и другие параметры при необходимости
    )

    return response


async def is_token_blacklisted(
    redis: Redis,
    token: str,
) -> bool:
    """
    Checks whether a given token is blacklisted.

    This function takes a given token, hashes it with a salt, and checks whether
    the hashed token exists in the Redis "blacklist:refresh" key. If the hashed
    token is found, it returns True, indicating that the token is blacklisted.
    Otherwise, it returns False.

    :param redis: The Redis instance to be used for checking the blacklist.
    :param token: The token to be checked against the blacklist.
    :return: A boolean indicating whether the token is blacklisted.
    """
    hashed_token = generate_hash_token(token)
    return await redis.exists(f"blacklist:refresh:{hashed_token}") == 1
