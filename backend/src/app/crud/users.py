from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from core.models import User
from core.schemas import UserCreate, UserUpdate
from utils.security import get_password_hash


async def get_user(db: AsyncSession, user_id: int) -> User | None:
    result = await db.execute(
        select(User).filter(User.id == user_id, User.is_active == True)
    )
    return result.scalars().first()


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(
        select(User).filter(User.email == email, User.is_active == True)
    )
    return result.scalars().first()


async def create_user(db: AsyncSession, user: UserCreate) -> User:
    hashed_password = get_password_hash(user.password)
    db_user = User(
        username=user.username,
        email=user.email,
        hashed_password=hashed_password,
        gender=user.gender,
        age=user.age,
        weight=user.weight,
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user


async def update_user(db: AsyncSession, user_id: int, user: UserUpdate) -> User | None:
    db_user = await get_user(db, user_id)
    if db_user:
        for key, value in user.model_dump().items():
            if value is not None:
                setattr(db_user, key, value)
        await db.commit()
        await db.refresh(db_user)
    return db_user


async def delete_user(db: AsyncSession, user_id: int) -> User | None:
    db_user = await get_user(db, user_id)
    if db_user:
        db_user.is_active = False  # Мягкое удаление
        await db.commit()
        await db.refresh(db_user)
    return db_user
