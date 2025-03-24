from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import (
    OAuth2PasswordRequestForm,
    HTTPBearer,
)
from sqlalchemy.ext.asyncio import AsyncSession

from db import db_helper
from core.logger import get_logger
from crud.user import create_user, get_user_by_email
from services.auth import (
    authenticate_user,
    create_access_token,
    create_refresh_token,
)
from schemas.auth import Token
from schemas.user import UserSchema

http_bearer = HTTPBearer(auto_error=False)

router = APIRouter(
    tags=["Authentication"],
    dependencies=[Depends(http_bearer)],
)
log = get_logger(__name__)


@router.post(
    "/register",
    response_model=UserSchema,
    status_code=status.HTTP_201_CREATED,
)
async def register_user(
    user_in: UserSchema,
    db: Annotated[AsyncSession, Depends(db_helper.session_getter)],
) -> UserSchema | None:
    """
    Registers a new user in the system.

    This endpoint creates a new user using the provided user data. If the email
    is already registered, it raises an HTTP 400 error. If user creation fails
    due to a database error, it raises an HTTP 500 error. Otherwise, the user
    is successfully registered and returned.

    Args:
        user_in (UserSchema): The data for creating a new user.
        db (Annotated[AsyncSession, Depends]): The async database session dependency.

    Returns:
        User | None: The created user object, or None if registration fails.

    Raises:
        HTTPException: If the email is already registered or if there's a database error.
    """
    log.info("Attempting to register user with email: %s", user_in.email)
    try:
        db_user = await get_user_by_email(db, user_in.email)
    except HTTPException as e:
        raise e
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
        return UserSchema.model_validate(user)


@router.post("/login", response_model=Token)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[AsyncSession, Depends(db_helper.session_getter)],
) -> Token | None:
    """
    Authenticates a user with the provided username and password.

    This endpoint authenticates a user based on the provided username and
    password. If the authentication is successful, it returns a Token object
    containing the access token and the refresh token. The access token should
    be used to access protected endpoints, while the refresh token is used to
    obtain a new access token when the current one expires.

    Args:
        form_data (OAuth2PasswordRequestForm): The form data containing the
            username and password of the user to authenticate.
        db (Annotated[AsyncSession, Depends]): The async database session
            dependency.

    Returns:
        Token | None: The authentication tokens, or None if authentication fails.

    Raises:
        HTTPException: If the authentication fails.
    """
    log.info("Attempting login for user: %s", form_data.username)
    try:
        user = await authenticate_user(
            db,
            form_data.username,
            form_data.password,
        )
        access_token = create_access_token(user)
        refresh_token = create_refresh_token(user)

    except HTTPException as e:
        raise e
    log.info("User logged in successfully: %s", form_data.username)
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
    )
