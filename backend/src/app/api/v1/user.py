from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from crud.user import get_user, create_user, update_user, delete_user, get_user_by_email
from core.schemas.user import UserCreate, UserUpdate, UserRead, DeletedUser
from core.models import db_helper

router = APIRouter(tags=["user"])


@router.post("/", response_model=UserRead)
async def create_user_endpoint(
    user_in: UserCreate, db: Annotated[AsyncSession, Depends(db_helper.session_getter)]
):
    user = await get_user_by_email(db, user_in.email)
    if user:
        raise HTTPException(
            status_code=400, detail="User with this email already exists"
        )
    return await create_user(db, user_in)


@router.get("/{user_id}", response_model=UserRead)
async def read_user_endpoint(
    user_id: int, db: Annotated[AsyncSession, Depends(db_helper.session_getter)]
):
    db_user = await get_user(db, user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user


@router.put("/{user_email}", response_model=UserRead)
async def update_user_endpoint(
    user_email: EmailStr,
    user: UserUpdate,
    db: Annotated[AsyncSession, Depends(db_helper.session_getter)],
):
    db_user = await update_user(db, user_email, user)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user


@router.delete("/{user_id}", response_model=DeletedUser)
async def delete_user_endpoint(
    user_id: int, db: Annotated[AsyncSession, Depends(db_helper.session_getter)]
):
    deleted_user = await delete_user(db, user_id)
    if deleted_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return deleted_user
