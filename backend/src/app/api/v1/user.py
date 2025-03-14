from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.user import get_user, create_user, update_user, delete_user
from core.schemas.user import UserCreate, UserUpdate, UserRead, DeletedUser
from core.models import db_helper

router = APIRouter(prefix="/users", tags=["users"])


@router.post("/", response_model=UserRead)
async def create_user_endpoint(
    user: UserCreate, db: AsyncSession = Depends(db_helper.session_getter)
):
    return await create_user(db, user)


@router.get("/{user_id}", response_model=UserRead)
async def read_user_endpoint(
    user_id: int, db: AsyncSession = Depends(db_helper.session_getter)
):
    db_user = await get_user(db, user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user


@router.put("/{user_id}", response_model=UserRead)
async def update_user_endpoint(
    user_id: int, user: UserUpdate, db: AsyncSession = Depends(db_helper.session_getter)
):
    db_user = await update_user(db, user_id, user)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user


@router.delete("/{user_id}", response_model=DeletedUser)
async def delete_user_endpoint(
    user_id: int, db: AsyncSession = Depends(db_helper.session_getter)
):
    deleted_user = await delete_user(db, user_id)
    if deleted_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return deleted_user
