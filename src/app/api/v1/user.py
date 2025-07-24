from datetime import datetime
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    status,
)
from fastapi.responses import ORJSONResponse, HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.core.logger import get_logger
from src.app.crud.profile import update_user_profile, get_user_profile
from src.app.db import db_helper
from src.app.schemas.user import UserProfile, UserResponse
from src.app.services.auth import get_current_auth_user
from src.app.utils.security import generate_csp_nonce
from src.app.utils.templates import templates

router = APIRouter(
    tags=["User"],
    default_response_class=ORJSONResponse,
)

log = get_logger("user_api")

UNAUTHORIZED_EXCEPTION = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail={"message": "Время сессии истекло. Пожалуйста, войдите заново"},
)


@router.get("/me")
async def read_current_user(
    user: Annotated[UserResponse, Depends(get_current_auth_user)],
):
    """
    Retrieves the current authenticated user's basic information.

    This endpoint returns the username and email of the authenticated user.
    If the user is not authenticated, it raises an HTTPException with a 401 status code.

    :param user: The authenticated user object obtained from the dependency.
    :return: A dictionary containing the username and email of the user.
    :raises HTTPException: If the user is not authenticated.
    """
    if user is None:
        raise UNAUTHORIZED_EXCEPTION

    return {
        "username": user.username,
        "email": user.email,
    }


@router.get("/profile/data", response_class=HTMLResponse)
@router.head("/profile/data")
async def get_profile(
    request: Request,
    user: Annotated[UserResponse, Depends(get_current_auth_user)],
    session: Annotated[AsyncSession, Depends(db_helper.session_getter)],
):
    """
    Retrieves the current authenticated user's profile information.

    This endpoint returns the profile information of the authenticated user.
    If the user is not authenticated, it raises an HTTPException with a 401 status code.

    :param request: The incoming request object.
    :param user: The authenticated user object obtained from the dependency.
    :param session: The current database session.
    :return: A rendered HTML template with the user's profile information.
    :raises HTTPException: If the user is not authenticated.
    """
    if user is None:
        log.error("Пользователь не авторизован")
        raise UNAUTHORIZED_EXCEPTION

    user = await get_user_profile(session, user.id)
    return templates.TemplateResponse(
        name="profile.html",
        request=request,
        context={
            "current_year": datetime.now().year,
            "csp_nonce": generate_csp_nonce(),
            "user": user,
            "is_filled": all(
                (user.gender, user.age, user.weight, user.height, user.kfa)
            ),
        },
    )


@router.post("/profile/update")
async def update_profile(
    data_in: UserProfile,
    user: Annotated[UserResponse, Depends(get_current_auth_user)],
    session: Annotated[AsyncSession, Depends(db_helper.session_getter)],
):
    """
    Updates the current authenticated user's profile information.

    This endpoint accepts a `UserProfile` object containing the updated
    profile details and updates the current user's profile in the database.
    If the user is not authenticated, it raises a 401 HTTPException. If
    the provided data is invalid, it raises a 400 HTTPException.

    :param data_in: The updated user profile information.
    :param user: The authenticated user object obtained from the dependency.
    :param session: The current database session.
    :return: A JSON response indicating the success of the profile update.
    :raises HTTPException: If the user is not authenticated or if the provided data is invalid.
    """
    if user is None:
        raise UNAUTHORIZED_EXCEPTION

    if not data_in:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": "Произошла ошибка. Попробуйте позже!",
            },
        )
    await update_user_profile(data_in, user, session)

    return {"message": "Profile updated successfully"}

#
#
# @router.delete("/me/", response_model=UserDelete)
# async def delete_current_user(
#     db: Annotated[AsyncSession, Depends(db_helper.session_getter)],
#     user: Annotated[UserRead, Depends(get_current_user)],
# ):
#     deleted_user = await delete_user(db, user)
#     if deleted_user is None:
#         raise HTTPException(status_code=404, detail="User not found")
#     return deleted_user
