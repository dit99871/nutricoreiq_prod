from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from db import db_helper
from utils import create_jwt
from core.config import settings
from core.logger import get_logger
from crud.user import create_user, get_user_by_email
from services.auth import authenticate_user
from schemas.auth import Token
from schemas.user import UserCreate, UserRead

router = APIRouter(tags=["Authentication"])
log = get_logger(__name__)


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
)
async def register_user(
    user_in: UserCreate,
    db: Annotated[AsyncSession, Depends(db_helper.session_getter)],
):
    log.info("Attempting to register user with email: %s", user_in.email)
    try:
        db_user = await get_user_by_email(db, user_in.email)
    except HTTPException as e:
        raise e
    except Exception as e:
        HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
    else:
        if db_user:
            log.warning(
                "Registration failed: Email already registered: %s", user_in.email
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )
        user = await create_user(db, user_in)
        if not user:
            log.error(
                "Registration failed: Database error creating user: %s", user_in.email
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create user",
            )
        log.info("User registered successfully: %s", user.email)
        return user


@router.post("/login", response_model=Token)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[AsyncSession, Depends(db_helper.session_getter)],
):
    log.info("Attempting login for user: %s", form_data.username)
    try:
        payload = await authenticate_user(
            db,
            form_data.username,
            form_data.password,
        )
        access_token = create_jwt(
            payload.model_dump(),
            timedelta(minutes=settings.auth.access_token_expires),
        )
        refresh_token = create_jwt(
            payload.model_dump(),
            timedelta(days=settings.auth.refresh_token_expires),
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        log.error(f"Error creating token: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creating token",
        )
    log.info("User logged in successfully: %s", form_data.username)
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
    )
