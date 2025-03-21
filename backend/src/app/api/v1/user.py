from typing import Annotated

from fastapi import APIRouter, Depends

from schemas.user import UserRead
from services.auth import get_current_auth_user

router = APIRouter(tags=["User"])


@router.get("/me", response_model=UserRead)
async def read_current_user(
    current_user: Annotated[UserRead, Depends(get_current_auth_user)],
):
    return current_user


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
