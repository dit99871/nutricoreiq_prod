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


async def create_response(user: UserPublic) -> ORJSONResponse:
    """
    Creates an ORJSONResponse object with the user's access and refresh tokens.

    :param user: The user object for which to create the tokens.
    :return: An ORJSONResponse object with the access and refresh tokens.
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
