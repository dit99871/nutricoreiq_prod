"""JWT token service for handling token creation and validation."""

import datetime as dt
import uuid
from datetime import datetime, timedelta
from typing import Any

from fastapi import HTTPException
from jose import jwt, ExpiredSignatureError, JWTError
from starlette import status

from src.app.core.config import settings
from src.app.core.exceptions import ExpiredTokenException
from src.app.core.logger import get_logger
from src.app.core.services.redis import add_refresh_to_redis
from src.app.schemas.user import UserPublic

log = get_logger("jwt_service")

TOKEN_TYPE_FIELD = "type"
ACCESS_TOKEN_TYPE = "access"
REFRESH_TOKEN_TYPE = "refresh"


def create_jwt(
    token_type: str,
    token_data: dict,
    expire_minutes: int = settings.auth.access_token_expires,
    expire_timedelta: timedelta | None = None,
) -> str:
    """
    Creates a JWT token with the given payload and expiration duration.

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
    encoded: str = encode_jwt(
        payload=jwt_payload,
        expire_minutes=expire_minutes,
        expire_timedelta=expire_timedelta,
    )
    return encoded


def create_access_jwt(user: UserPublic) -> str:
    """
    Creates an access token for the given user.

    :param user: The user object for which to create the token.
    :return: The encoded JWT token as a string.
    """
    jwt_payload = {
        "sub": str(user.uid),
        "username": user.username,
        "email": user.email,
    }
    return create_jwt(
        token_type=ACCESS_TOKEN_TYPE,
        token_data=jwt_payload,
        expire_minutes=settings.auth.access_token_expires,
    )


async def create_refresh_jwt(user: UserPublic) -> str:
    """
    Creates a refresh token for the given user.

    :param user: The user object for which to create the token.
    :return: The encoded JWT token as a string.
    """
    jwt_payload = {
        "sub": user.uid,
    }
    jwt_expires = timedelta(days=settings.auth.refresh_token_expires)

    refresh_jwt = create_jwt(
        token_type=REFRESH_TOKEN_TYPE,
        token_data=jwt_payload,
        expire_timedelta=jwt_expires,
    )
    await add_refresh_to_redis(
        uid=user.uid,
        jwt=refresh_jwt,
        exp=jwt_expires,
    )

    return refresh_jwt


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
        log.error("Файл с публичным ключом не найден: %s", e)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "message": "Ошибка авторизации",
                "details": {
                    "field": "file with public key",
                    "message": "File with public key not found.",
                },
            },
        )
    except ExpiredSignatureError as e:
        log.error("Токен истек: %s", e)
        raise ExpiredTokenException()

    except JWTError as e:
        log.error("Неверный токен: %s", e)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "message": "Неверный токен. Пожалуйста, войдите заново.",
            },
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
        log.error("Файл с приватным ключом не найден: %s", e)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "message": "Ошибка авторизации",
                "details": {
                    "field": "file with private key",
                    "message": "File with private key not found.",
                },
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
        log.error("JWT ошибка при кодировании токена: %s", e)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "message": "Ошибка авторизации",
                "details": {
                    "field": "encode token",
                    "message": "JWT error encoding token",
                },
            },
        )
