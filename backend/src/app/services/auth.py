from typing import Annotated

from fastapi import Depends, Form, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.utils import db_helper, decode_token, verify_password
from crud.user import get_user_by_email, get_user_by_name
from schemas.auth import TokenPayload
from schemas.user import UserRead

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(db_helper.session_getter)],
) -> UserRead:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_token(token)
    if payload is None:
        raise credentials_exception
    email: EmailStr = payload.get("sub")
    if email is None:
        raise credentials_exception
    user = await get_user_by_email(db, email)
    if user is None:
        raise credentials_exception
    return UserRead.model_validate(user)


async def authenticate_user(
    db: Annotated[AsyncSession, Depends(db_helper.session_getter)],
    username: Form(),
    password: Form(),
) -> TokenPayload:
    unauthed_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid email or password",
    )
    user = await get_user_by_name(db, username)
    if not user or not verify_password(password, user.hashed_password):
        raise unauthed_exc
    return TokenPayload(sub=user.email, exp=settings)
