from typing import Annotated

from fastapi import APIRouter, Depends

from api.v1.auth import http_bearer
from schemas.user import UserSchema
from services.auth import get_current_token_payload, oauth2_scheme
from services.user import get_current_auth_user

router = APIRouter(tags=["User"], dependencies=[Depends(http_bearer)])


@router.get("/me")
async def read_current_user(
    user: Annotated[UserSchema, Depends(get_current_auth_user)],
    token: str = Depends(oauth2_scheme),
) -> dict:
    payload: dict = get_current_token_payload(token)
    iat = payload.get("iat")
    return {
        "username": user.username,
        "email": user.email,
        "logged_in_at": iat,
    }


#
# @router.patch("/me/", response_model=UserRead)
# async def update_current_user(
#     user_update: UserUpdate,
#     db: Annotated[AsyncSession, Depends(db_helper.session_getter)],
#     current_user: Annotated[UserRead, Depends(get_current_user)],
# ):
#     updated_user = await update_user(db, current_user.email, user_update)
#     if not updated_user:
#         raise HTTPException(status_code=400, detail="User not updated")
#     return updated_user
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
