"""JWT сервис для обработки создания и валидации токенов."""

import datetime as dt
import uuid
from datetime import datetime, timedelta
from typing import Any

from fastapi import Request
from jose import ExpiredSignatureError, JWTError, jwt

from src.app.core.exceptions import (
    AuthenticationError,
    ExternalServiceError,
)

from src.app.core.config import settings
from src.app.core.constants import (
    ACCESS_TOKEN_TYPE,
    CREDENTIAL_EXCEPTION,
    REFRESH_TOKEN_TYPE,
    TOKEN_TYPE_FIELD,
)
from src.app.core.exceptions import ExpiredTokenException
from src.app.core.logger import get_logger
from src.app.core.services.redis import add_refresh_jwt_to_redis
from src.app.core.schemas.user import UserPublic

log = get_logger("jwt_service")


def create_jwt(
    token_type: str,
    token_data: dict,
    expire_minutes: int = settings.auth.access_token_expires,
    expire_timedelta: timedelta | None = None,
) -> str:
    """
    Создает JWT токен с указанными данными и временем жизни.

    Создает JWT токен с указанным типом, данными и временем жизни.
    Время жизни может быть задано как в минутах, так и через timedelta.

    :param token_type: Тип создаваемого токена.
    :param token_data: Данные для включения в токен.
    :param expire_minutes: Время жизни токена в минутах.
    :param expire_timedelta: Время жизни токена в виде timedelta.
    :return: Закодированный JWT токен в виде строки.
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
    Создает access токен для пользователя.

    Генерирует JWT токен доступа с основными данными пользователя.

    :param user: Объект пользователя, для которого создается токен.
    :return: Закодированный JWT токен доступа.
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
    Создает refresh токен для пользователя.

    Генерирует JWT токен обновления и сохраняет его в Redis.

    :param user: Объект пользователя, для которого создается токен.
    :return: Закодированный JWT refresh токен.
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
    await add_refresh_jwt_to_redis(
        uid=user.uid,
        jwt=refresh_jwt,
        exp=jwt_expires,
    )

    return refresh_jwt


def decode_jwt(token: str) -> dict[str, Any] | None:
    """
    Декодирует JWT токен.

    Пытается декодировать переданный JWT токен с использованием публичного ключа.

    :param token: JWT токен для декодирования.
    :return: Декодированные данные токена или None.
    :raises ExternalServiceError: Если файл с публичным ключом не найден, токен истек или произошла ошибка JWT.
    :raises ExpiredSignatureError: Если истек срок жизни токена
    :raises AuthenticationError: Если токен неверен
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
        raise ExternalServiceError(
            "Ошибка авторизации",
            service_name="JWT Service",
            original_error=e,
        )
    except ExpiredSignatureError as e:
        log.error("Токен истек: %s", e)
        raise ExpiredTokenException()

    except JWTError as e:
        log.error("Неверный токен: %s", e)
        raise AuthenticationError("Неверный токен. Пожалуйста, войдите заново.")


def encode_jwt(
    payload: dict,
    algorithm: str = settings.auth.algorithm,
    expire_minutes: int = settings.auth.access_token_expires,
    expire_timedelta: dt.timedelta | None = None,
) -> str:
    """
    Кодирует данные в JWT токен.

    Кодирует переданные данные в JWT токен с использованием приватного ключа.

    :param payload: Данные для кодирования.
    :param algorithm: Алгоритм шифрования (по умолчанию из настроек).
    :param expire_minutes: Время жизни токена в минутах.
    :param expire_timedelta: Время жизни токена в виде timedelta.
    :return: Закодированный JWT токен.
    :raises ExternalServiceError: Если файл с приватным ключом не найден или произошла ошибка кодирования.
    """

    try:
        private_key = settings.auth.private_key_path.read_text()

    except FileNotFoundError as e:
        log.error("Файл с приватным ключом не найден: %s", e)
        raise ExternalServiceError(
            "Ошибка авторизации",
            service_name="JWT Service",
            original_error=e,
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
        raise ExternalServiceError(
            "Ошибка авторизации",
            service_name="JWT Service",
            original_error=e,
        )


async def get_jwt_from_cookies(
    request: Request,
    token_type: str = ACCESS_TOKEN_TYPE,
) -> str:
    """
    Извлекает JWT токен из cookies запроса.

    :param request: Объект текущего запроса.
    :param token_type: Тип токена (по умолчанию 'access').
    :return: Значение JWT токена или None, если токен не найден.
    """

    token = request.cookies.get(token_type)

    return token


async def get_jwt_payload(token: str) -> dict[str, Any]:
    """
    Получает и валидирует полезную нагрузку из JWT токена.

    :param token: JWT токен для декодирования.
    :return: Декодированная полезная нагрузка токена.
    :raises AuthenticationError: Если не удалось декодировать токен.
    """

    payload: dict[str, Any] | None = decode_jwt(token)
    if payload is None:
        log.error("Ошибка декодирования токена: payload is None")
        raise CREDENTIAL_EXCEPTION

    return payload
