from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.models import db_helper
from core.schemas.auth import Token, TokenPayload
from core.schemas.user import UserCreate, UserRead
from crud.user import create_user, get_user_by_email
from services.auth import authenticate_user
from utils.logger import get_logger
from utils.security import (
    get_password_hash,
    create_token,
    decode_token,
)

router = APIRouter(tags=["Authentication"])
log = get_logger(__name__)


@router.post("/register/", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_in: UserCreate,
    db: Annotated[AsyncSession, Depends(db_helper.session_getter)],
):
    log.info("Attempting to register user with email: %s", user_in.email)
    db_user = await get_user_by_email(db, user_in.email)
    if db_user:
        log.warning("Registration failed: Email already registered: %s", user_in.email)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )
    user_in.password = get_password_hash(user_in.password)
    user = await create_user(db, user_in)
    if not user:
        log.error(
            "Registration failed: Database error creating user: %s", user_in.email
        )
        raise HTTPException(
            status_code=500,
            detail="Failed to create user",
        )
    log.info("User registered successfully: %s", user.email)
    return user


@router.post("/login/", response_model=Token)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[AsyncSession, Depends(db_helper.session_getter)],
):
    log.info("Attempting login for user: %s", form_data.username)
    payload = await authenticate_user(
        db,
        form_data.username,
        form_data.password,
    )
    access_token = create_token(
        payload.model_dump(),
        timedelta(minutes=settings.auth.access_token_expires),
    )
    refresh_token = create_token(
        payload.model_dump(),
        timedelta(days=settings.auth.refresh_token_expires),
    )
    log.info("User logged in successfully: %s", form_data.username)
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
    )


@router.post("/refresh/", response_model=Token)
async def is_refresh_token(token: str):
    log.info("Attempting to refresh token")
    payload = decode_token(token)
    if not payload:
        log.warning("Refresh token failed: Invalid refresh token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )
    email = payload.get("sub")
    role = payload.get("role")
    if not email or not role:
        log.warning("Refresh token failed: Invalid refresh token payload")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token payload",
        )
    access_token_payload = TokenPayload(
        sub=email,
        role=role,
        exp=settings.auth.access_token_expires,
    )
    access_token = create_token(
        access_token_payload.model_dump(),
        timedelta(minutes=settings.auth.access_token_expires),
    )
    log.info("Token refreshed successfully for user: %s", email)
    return Token(
        access_token=access_token,
        refresh_token=token,
        token_type="bearer",
    )
