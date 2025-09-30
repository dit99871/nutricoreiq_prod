from typing import Any

from fastapi import Request

from src.app.core.constants import CREDENTIAL_EXCEPTION
from src.app.core.logger import get_logger
from src.app.core.services.jwt_service import (
    ACCESS_TOKEN_TYPE,
    TOKEN_TYPE_FIELD,
    decode_jwt,
)

log = get_logger("auth_service")


async def get_access_token_from_cookies(request: Request) -> str | None:
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


def get_current_access_token_payload(
    token: str,
) -> dict[str, Any]:
    """
    Retrieves the payload of the current access token.

    This function takes the given access token and attempts to decode it
    using the decode_jwt function. If the decoding fails, a 401 HTTP
    exception is raised with an appropriate error message. If the
    "type" field in the payload is not "access", a 401 HTTP exception is
    also raised.

    :param token: The access token to be decoded.
    :return: The payload of the access token as a dictionary.
    :raises HTTPException: If the decoding fails or the "type" field is
                           not "access".
    """

    log.debug("Attempting to decode token: %s", token)

    payload: dict[str, Any] | None = decode_jwt(token)
    if payload is None:
        log.error("Failed to decode token: payload is None")
        raise CREDENTIAL_EXCEPTION

    token_type: str | None = payload.get(TOKEN_TYPE_FIELD)
    if token_type is None or token_type != ACCESS_TOKEN_TYPE:
        log.error(
            "No match for token type in token payload: %s",
            payload,
        )
        raise CREDENTIAL_EXCEPTION

    return payload
