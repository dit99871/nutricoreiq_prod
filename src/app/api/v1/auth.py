from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
    Request,
)
from fastapi.responses import ORJSONResponse
from fastapi.security import (
    OAuth2PasswordRequestForm,
    HTTPBearer,
)
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from db import db_helper
from core.logger import get_logger
from core.redis import get_redis
from crud.user import create_user, get_user_by_email
from services.auth import (
    create_access_jwt,
    create_refresh_jwt,
)
from services.user import (
    authenticate_user,
    get_current_auth_user_for_refresh,
    get_current_auth_user,
)
from schemas.user import UserCreate, UserResponse
from utils.auth import create_response

log = get_logger("auth_api")
http_bearer = HTTPBearer(auto_error=False)

router = APIRouter(
    tags=["Authentication"],
    default_response_class=ORJSONResponse,
    dependencies=[Depends(http_bearer)],
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
    log.info("Attempting to register user with email: %s", user_in.email)
    try:
        db_user = await get_user_by_email(session, user_in.email)
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
        user = await create_user(session, user_in)
        if not user:
            log.error(
                "Registration failed: Database error creating user: %s", user_in.email
            )
            await session.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create user",
            )
        log.info("User registered successfully: %s", user.email)
        return user


@router.post("/login")
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: Annotated[AsyncSession, Depends(db_helper.session_getter)],
):
    log.info("Attempting login for user: %s", form_data.username)

    try:
        user = await authenticate_user(
            session,
            form_data.username,
            form_data.password,
        )
        access_jwt = create_access_jwt(user)
        refresh_jwt = await create_refresh_jwt(user)

        response = create_response(
            access_token=access_jwt,
            refresh_token=refresh_jwt,
        )

        log.info("User logged in successfully: %s", form_data.username)
        return response

    except HTTPException as e:
        log.error("Login failed for user %s: %s", form_data.username, str(e))
        raise e

    except Exception as e:
        log.exception("Unexpected error logging in: %s", e)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Unexpected error logging in: {e!r}",
        )


@router.post(
    "/refresh",
    response_model_exclude_none=True,
)
async def refresh_token(
    request: Request,
    session: AsyncSession = Depends(db_helper.session_getter),
    redis: Redis = Depends(get_redis),
):
    refresh_jwt = request.cookies.get("refresh_token")
    if not refresh_jwt:
        log.error("Refresh token not found in cookies")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No refresh token found in cookies",
        )

    try:
        user = await get_current_auth_user_for_refresh(refresh_jwt, session, redis)
        access_jwt = create_access_jwt(user)
        refresh_jwt = await create_refresh_jwt(user)

        response = create_response(
            access_token=access_jwt,
            refresh_token=refresh_jwt,
        )

    except HTTPException as e:
        raise e

    except Exception as e:
        log.exception("Unexpected error refreshing tokens: %s", e)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Unexpected error refreshing tokens: {e!r}",
        )

    return response


@router.post("/password/change")
async def change_password():
    pass
