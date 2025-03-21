from typing import Annotated, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.logger import get_logger
from db import db_helper
from utils import decode_token, verify_password
from crud.user import get_user_by_email, get_user_by_name
from schemas.auth import TokenPayload
from schemas.user import UserRead

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login")
log = get_logger(__name__)

CREDENTIAL_EXCEPTION = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_auth_payload(token: str) -> Optional[EmailStr]:
    log.debug("Attempting to decode token: %s", token)

    payload: Optional[dict] = decode_token(token)
    if payload is None:
        log.error("Failed to decode token: payload is None")
        raise CREDENTIAL_EXCEPTION

    email: Optional[EmailStr] = payload.get("sub")
    if email is None:
        log.error("Email not found in token payload: %s", payload)
        raise CREDENTIAL_EXCEPTION

    return email


async def get_current_auth_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(db_helper.session_getter)],
) -> UserRead:
    try:
        email: Optional[EmailStr] = get_current_auth_payload(token)

        log.debug("Looking for user with email: %s", email)
        user = await get_user_by_email(db, email)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
    if user is None:
        log.error("User not found for email: %s", email)
        raise CREDENTIAL_EXCEPTION

    log.info("User authenticated successfully: %s", email)
    return UserRead.model_validate(user)


async def authenticate_user(
    db: Annotated[AsyncSession, Depends(db_helper.session_getter)],
    username: str,
    password: str,
) -> TokenPayload:
    log.debug("Attempting to authenticate user: %s", username)
    unauthed_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid email or password",
    )
    try:
        user = await get_user_by_name(db, username)
    except HTTPException as e:
        raise e
    except Exception as e:
        HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
    else:
        if user is None:
            log.error("User not found: %s", username)
            raise unauthed_exc

        log.debug("User found: %s. Verifying password.", username)
        if not verify_password(password, user.hashed_password):
            log.error("Invalid password for user: %s", username)
            raise unauthed_exc

        log.info("User authenticated successfully: %s", username)
        return TokenPayload(
            sub=user.email,
            exp=settings.auth.access_token_expires,
        )
