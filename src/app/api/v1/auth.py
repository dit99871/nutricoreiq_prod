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
from sqlalchemy.ext.asyncio import AsyncSession

from db import db_helper
from core.logger import get_logger
from crud.user import create_user, get_user_by_email
from services.auth import (
    create_access_jwt,
    create_refresh_jwt,
    get_current_token_payload,
)
from services.user import (
    authenticate_user,
    get_current_auth_user_for_refresh,
)
from schemas.user import UserCreate, UserResponse
from utils.auth import create_response

http_bearer = HTTPBearer(auto_error=False)

router = APIRouter(
    tags=["Authentication"],
    dependencies=[Depends(http_bearer)],
)
log = get_logger(__name__)


@router.post(
    "/register",
    response_model=UserCreate,
    status_code=status.HTTP_201_CREATED,
)
async def register_user(
    user_in: UserCreate,
    db: Annotated[AsyncSession, Depends(db_helper.session_getter)],
) -> UserCreate | None:
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
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create user",
            )
        log.info("User registered successfully: %s", user.email)
        return user


@router.post("/login")
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[AsyncSession, Depends(db_helper.session_getter)],
) -> ORJSONResponse:
    log.info("Attempting login for user: %s", form_data.username)

    try:
        user = await authenticate_user(
            db,
            form_data.username,
            form_data.password,
        )
        access_token = create_access_jwt(user)
        refresh_token = await create_refresh_jwt(user, db)

        response = create_response(
            access_token=access_token,
            refresh_token=refresh_token,
        )

        log.info("User logged in successfully: %s", form_data.username)
        return response

    except HTTPException as e:
        log.error("Login failed for user %s: %s", form_data.username, str(e))
        raise e


@router.post(
    "/refresh",
    response_model_exclude_none=True,
)
async def refresh_tokens(
    request: Request,
    user: UserResponse = Depends(get_current_auth_user_for_refresh),
    db: AsyncSession = Depends(db_helper.session_getter),
) -> ORJSONResponse:
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        log.error("Refresh token not found in cookies for user: %s", user.username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No refresh token found",
        )
    payload = get_current_token_payload(refresh_token)

    try:
        access_token = create_access_jwt(user)
        refresh_token = await create_refresh_jwt(user, db)

        response = create_response(
            access_token=access_token,
            refresh_token=refresh_token,
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
