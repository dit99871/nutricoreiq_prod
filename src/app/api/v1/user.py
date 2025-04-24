from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import ORJSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from crud.profile import update_user_profile, get_user_profile
from db import db_helper
from schemas.user import UserProfile, UserResponse, UserAccount
from services.auth import get_current_auth_user
from utils.security import generate_csp_nonce
from utils.templates import templates

router = APIRouter(
    tags=["User"],
    default_response_class=ORJSONResponse,
)


@router.get("/me", response_class=ORJSONResponse)
async def read_current_user(
    user: Annotated[UserResponse, Depends(get_current_auth_user)],
):
    """
    Retrieves the current authenticated user's information.

    This endpoint returns the username and email of the authenticated user.

    :param user: The authenticated user object obtained from the dependency.
    :return: A dictionary containing the username and email of the user.
    """
    return {
        "username": user.username,
        "email": user.email,
    }


@router.get(
    "/profile/data",
    response_model=UserAccount,
    response_model_exclude_unset=True,
)
async def get_profile(
    request: Request,
    current_user: Annotated[UserResponse, Depends(get_current_auth_user)],
    session: Annotated[AsyncSession, Depends(db_helper.session_getter)],
):
    """
    Retrieves the current authenticated user's profile information.

    This endpoint returns the username, email, joined date, and last seen date
    of the authenticated user.

    :param request: The incoming request object.
    :param current_user: The authenticated user object obtained from the dependency.
    :param session: The database session to use for the query.
    :return: A UserAccount object containing the user's profile information.
    :raises HTTPException: If the user is not found in the database.
    """
    try:
        user = await get_user_profile(session, current_user.id)
        return templates.TemplateResponse(
            name="profile.html",
            request=request,
            context={
                "csp_nonce": generate_csp_nonce(),
                "user": user,
                "is_filled": all(
                    (user.gender, user.age, user.weight, user.height, user.kfa)
                ),
            },
        )
    except HTTPException as e:
        raise e


@router.post("/profile/update", response_class=ORJSONResponse)
async def update_profile(
    data_in: UserProfile,
    current_user: Annotated[UserResponse, Depends(get_current_auth_user)],
    session: Annotated[AsyncSession, Depends(db_helper.session_getter)],
):
    """
    Updates the current authenticated user's profile information.

    This endpoint takes a `UserProfile` object as input and updates the user's
    profile information in the database. The function attempts to update the
    user's profile information in the database and commits the changes.

    :param data_in: A `UserProfile` instance containing the new profile data.
    :param current_user: The authenticated user whose profile is to be updated.
    :param session: The current database session.
    :raises HTTPException: If the user is not found or an error occurs during the update.
    :return: A JSON response indicating success if the update is successful.
    """
    if not data_in:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No data provided for update",
        )
    try:
        await update_user_profile(data_in, current_user, session)
        return {"message": "Profile updated successfully"}
    except HTTPException as e:
        raise e


#
#
# @router.delete("/me/", response_model=UserDelete)
# async def delete_current_user(
#     db: Annotated[AsyncSession, Depends(db_helper.session_getter)],
#     current_user: Annotated[UserRead, Depends(get_current_user)],
# ):
#     deleted_user = await delete_user(db, current_user)
#     if deleted_user is None:
#         raise HTTPException(status_code=404, detail="User not found")
#     return deleted_user
