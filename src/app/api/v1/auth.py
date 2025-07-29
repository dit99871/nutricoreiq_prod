from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
    Request,
)
from fastapi.responses import ORJSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.db import db_helper
from src.app.core.logger import get_logger
from src.app.core.redis import get_redis
from src.app.crud.user import create_user, get_user_by_email
from src.app.schemas.user import PasswordChange, UserCreate, UserResponse
from src.app.services.auth import (
    add_tokens_to_response,
    create_access_jwt,
    create_refresh_jwt,
    update_password,
    get_current_auth_user,
    get_current_auth_user_for_refresh,
    authenticate_user,
)
from src.app.services.email import send_welcome_email
from src.app.services.redis import revoke_refresh_token
from src.app.utils.auth import create_response

log = get_logger("auth_api")

router = APIRouter(
    tags=["Authentication"],
    default_response_class=ORJSONResponse,
)


@router.post(
    "/register",
    response_model=UserCreate,
    status_code=status.HTTP_201_CREATED,
)
async def register_user(
    user_in: UserCreate,
    session: Annotated[AsyncSession, Depends(db_helper.session_getter)],
) -> UserCreate | None:
    """
    Registers a new user in the database.

    Given a valid `UserCreate` object, registers a new user in the database.
    If the user is already registered, raises an `HTTPException` with a 400
    status code and a detail string containing the error message.

    :param user_in: The user data to register.
    :param session: The database session to use for the query.
    :return: The registered user object.
    :raises HTTPException: If the user is already registered.
    """
    # log.info("Attempting to register user with email: %s", user_in.email)
    db_user = await get_user_by_email(session, user_in.email)

    if db_user:
        log.warning("Registration failed: Email already registered: %s", user_in.email)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": "Пользователь с таким email уже зарегистрирован",
            },
        )
    user = await create_user(session, user_in)
    log.info("User registered successfully: %s", user.email)

    await send_welcome_email(user_in.email)

    return user


@router.post("/login")
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: Annotated[AsyncSession, Depends(db_helper.session_getter)],
) -> UserResponse:
    """
    Logs a user in and returns a response containing an access and refresh token.

    Given a valid username and password, logs the user in and returns a response
    containing an access and refresh token.

    :param form_data: The username and password to log in with.
    :param session: The current database session.
    :return: A response containing an access and refresh token.
    """
    user = await authenticate_user(
        session,
        form_data.username,
        form_data.password,
    )
    response = await add_tokens_to_response(user)

    # log.info("User logged in successfully: %s", form_data.username)
    return response


@router.post("/logout")
async def logout(
    request: Request,
    user: Annotated[UserResponse, Depends(get_current_auth_user)],
    redis: Redis = Depends(get_redis),
):
    """
    Logs out a user and invalidates their refresh token.

    This endpoint logs out a user, invalidates their refresh token, and clears
    the access and refresh tokens from the request cookies.

    :param request: The current request object.
    :param user: The authenticated user object.
    :param redis: The Redis client to use for invalidating the refresh token.
    :return: A RedirectResponse to the root URL, with the access and refresh
             tokens cleared from the cookies.
    :raises HTTPException: If the refresh token is not found in the request
                           cookies.
    """
    refresh_jwt = request.cookies.get("refresh_token")
    if not refresh_jwt:
        log.error("Refresh token not found in cookies")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "message": "Внутренняя ошибка сервера",
                "details": {
                    "field": "logout",
                    "message": "Refresh token not found in cookies",
                },
            },
        )
    await revoke_refresh_token(user.uid, refresh_jwt, redis)

    session_id = request.cookies.get("redis_session_id")
    if session_id:
        await redis.delete(f"redis_session:{session_id}")

    response = ORJSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "Successfully logged out"},
    )

    response.delete_cookie("refresh_token")
    response.delete_cookie("access_token")
    response.delete_cookie("redis_session_id")

    return response


@router.post(
    "/refresh",
    response_model_exclude_none=True,
)
async def refresh_token(
    request: Request,
    session: AsyncSession = Depends(db_helper.session_getter),
    redis: Redis = Depends(get_redis),
):
    """
    Refreshes the access and refresh tokens for a given user.

    This endpoint takes a refresh token from the request cookies and returns a
    response containing a new access and refresh token if the refresh token is
    valid. If the refresh token is invalid or has expired, it raises a 401
    HTTP exception.

    :param request: The current request object.
    :param session: The current database session.
    :param redis: The Redis client to use for validating the refresh token.
    :return: A response containing the new access and refresh tokens.
    :raises HTTPException: If the refresh token is not found in the request
                           cookies, or if the refresh token is invalid or has
                           expired.
    """
    refresh_jwt = request.cookies.get("refresh_token")
    if not refresh_jwt:
        log.error("Refresh token not found in cookies")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "message": "Ошибка аутентификации. Пожалуйста, войдите заново",
                "details": "Refresh token not found in cookies",
            },
        )

    user = await get_current_auth_user_for_refresh(refresh_jwt, session, redis)
    access_jwt = create_access_jwt(user)
    refresh_jwt = await create_refresh_jwt(user)

    response = create_response(
        access_token=access_jwt,
        refresh_token=refresh_jwt,
    )

    return response


@router.post("/password/change")
async def change_password(
    password_data: PasswordChange,
    request: Request,
    user: Annotated[UserResponse, Depends(get_current_auth_user)],
    session: AsyncSession = Depends(db_helper.session_getter),
):
    """
    Changes the password for the authenticated user.

    Given a valid username and old password, this endpoint changes the
    password for the authenticated user to the new password provided in the
    request.

    :param password_data: The new password and the old password to change.
    :param request: The current request object.
    :param user: The authenticated user object.
    :param session: The current database session.
    :return: A response containing the new access and refresh tokens.
    :raises HTTPException: If the old password is incorrect.
    :raises HTTPException: If an unexpected error occurs while changing the
                           password.
    """
    authenticated_user = await authenticate_user(
        session, user.username, password_data.current_password
    )

    return await update_password(
        authenticated_user, session, password_data.new_password
    )
