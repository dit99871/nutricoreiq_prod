"""Утилиты для работы с аутентификацией"""

import datetime as dt

import bcrypt
from fastapi import status
from fastapi.responses import ORJSONResponse

from src.app.core.config import settings
from src.app.core.constants import ACCESS_TOKEN_TYPE, REFRESH_TOKEN_TYPE
from src.app.core.logger import get_logger
from src.app.core.services.jwt_service import create_access_jwt, create_refresh_jwt
from src.app.core.schemas.user import UserPublic

log = get_logger("auth_utils")


def get_password_hash(password: str) -> bytes:
    """
    Возвращает хеш пароля в виде байтов.

    Хеширует переданный пароль со случайной солью и возвращает в виде байтов.

    :param password: Пароль для хеширования.
    :return: Хешированный пароль в виде байтов.
    """
    salt = bcrypt.gensalt()

    return bcrypt.hashpw(password.encode(), salt)


def verify_password(
    password: str,
    hashed_password: bytes,
) -> bool:
    """
    Проверяет, соответствует ли пароль хешированному паролю.

    Сравнивает переданный пароль с хешированным паролем с помощью
    `bcrypt.checkpw` и возвращает `True`, если они совпадают, и `False` в противном случае.

    :param password: Пароль для проверки.
    :param hashed_password: Хешированный пароль для сравнения.
    :return: `True`, если пароль совпадает, `False` в противном случае.
    """

    return bcrypt.checkpw(
        password=password.encode(),
        hashed_password=hashed_password,
    )


async def create_response(user: UserPublic) -> ORJSONResponse:
    """
    Создает объект ORJSONResponse с токенами доступа пользователя.

    :param user: Объект пользователя, для которого создаются токены.
    :return: Объект ORJSONResponse с токенами доступа.
    """

    access_token = create_access_jwt(user)
    refresh_token = await create_refresh_jwt(user)

    response = ORJSONResponse(
        status_code=status.HTTP_200_OK,
        headers={
            "Cache-Control": "no-store",
            "Pragma": "no-cache",
        },
        content={
            "message": "Success",
        },
    )

    expires_refresh_token = dt.datetime.now(dt.UTC) + dt.timedelta(
        days=settings.auth.refresh_token_expires
    )
    expires_access_token = dt.datetime.now(dt.UTC) + dt.timedelta(
        minutes=settings.auth.access_token_expires
    )

    secure = settings.env.env == "prod"
    samesite = "strict" if secure else "lax"

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
            secure=secure,
            samesite=samesite,
            expires=expires,
        )

    _set_cookies(
        key=ACCESS_TOKEN_TYPE,
        value=access_token,
        expires=expires_access_token,
    )
    _set_cookies(
        key=REFRESH_TOKEN_TYPE,
        value=refresh_token,
        expires=expires_refresh_token,
    )

    return response
