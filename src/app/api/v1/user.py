from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import ORJSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from api.v1.auth import http_bearer
from crud.profile import update_user_profile, get_user_profile
from db import db_helper
from schemas.responses import ErrorResponse, SuccessResponse
from schemas.user import UserProfile, UserResponse, UserAccount
from services.user import get_current_auth_user
from utils.security import generate_csp_nonce
from utils.templates import templates

router = APIRouter(
    tags=["User"],
    default_response_class=ORJSONResponse,
    dependencies=[Depends(http_bearer)],
)


@router.get("/me", response_class=ORJSONResponse)
async def read_current_user(
    user: Annotated[UserResponse, Depends(get_current_auth_user)],
) -> dict:
    return {
        "username": user.username,
        "email": user.email,
    }


@router.get(
    "/profile/data",
    response_model=UserAccount,
    response_model_exclude_unset=True,
)
async def get_account(
    request: Request,
    current_user: Annotated[UserResponse, Depends(get_current_auth_user)],
    session: Annotated[AsyncSession, Depends(db_helper.session_getter)],
):
    try:
        user = await get_user_profile(session, current_user.id)
        return templates.TemplateResponse(
            name="profile.html",
            request=request,
            context={
                "user": user,
                "csp_nonce": generate_csp_nonce(),
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
