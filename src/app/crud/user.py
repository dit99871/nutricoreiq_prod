from fastapi import status
from fastapi.exceptions import HTTPException
from pydantic import EmailStr
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from core.logger import get_logger
from db.models import User
from schemas.user import UserCreate, UserResponse
from utils.auth import get_password_hash

log = get_logger("user_crud")


async def _get_user_by_filter(
    session: AsyncSession,
    filter_condition,
) -> UserResponse:
    try:
        stmt = select(User).filter(filter_condition, User.is_active == True)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        # if user is None:
        #     log.error("User not found in db")
        #     raise HTTPException(
        #         status_code=status.HTTP_404_NOT_FOUND,
        #         detail=f"User not found in db",
        #     )

        return UserResponse.model_validate(user) if user else None

    except SQLAlchemyError as e:
        log.error("Database error getting user: %s", e)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"DB error getting user: {str(e)}",
        )

    except Exception as e:
        log.exception("Unexpected error getting user: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error getting user {str(e)}",
        )


async def get_user_by_uid(
    session: AsyncSession,
    uid: str,
) -> UserResponse | None:
    try:
        user = await _get_user_by_filter(session, User.uid == uid)
        if user is None:
            log.error("User not found in db by uid")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User not found in db by uid",
            )
        return user

    except HTTPException as e:
        raise e


async def get_user_by_email(
    session: AsyncSession,
    email: EmailStr,
) -> UserResponse | None:
    try:
        user = await _get_user_by_filter(session, User.email == email)
        return user

    except HTTPException as e:
        raise e


async def get_user_by_name(
    session: AsyncSession,
    user_name: str,
) -> UserResponse | None:
    try:
        user = await _get_user_by_filter(session, User.username == user_name)
        if user is None:
            log.error("User not found in db by name")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User not found in db by name",
            )
        return user

    except HTTPException as e:
        raise e


async def create_user(
    session: AsyncSession,
    user_in: UserCreate,
) -> UserCreate | None:
    try:
        hashed_password = get_password_hash(user_in.password)
        db_user = User(
            **user_in.model_dump(
                exclude={"password"},
                # exclude_defaults=True,
            ),
            hashed_password=hashed_password,
        )
        session.add(db_user)
        await session.commit()
        await session.refresh(db_user)
        log.info("User created with email: %s", user_in.email)

        return user_in

    except SQLAlchemyError as e:
        log.error("Database error creating user_in with email %s: %s", user_in.email, e)
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )

    except Exception as e:
        log.exception(
            "Unexpected error creating user_in with email %s: %s", user_in.email, e
        )
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


#
#
# async def delete_user(
#     db: Annotated[AsyncSession, Depends(db_helper.session_getter)],
#     user_email: EmailStr,
#     user: UserDelete,
# ) -> Optional[DeletedUser]:
#     """Удаление пользователя."""
#     try:
#         db_user = await get_user_by_email(db, user_email)
#         if db_user:
#             # Создаем запись в таблице deleted_users
#             deleted_user = DeletedUser(
#                 username=db_user.username,
#                 email=db_user.email,
#                 hashed_password=db_user.hashed_password,
#                 gender=db_user.gender,
#                 age=db_user.age,
#                 weight=db_user.weight,
#                 is_active=db_user.is_active,
#             )
#             db.add(deleted_user)
#             await db.commit()
#             await db.refresh(deleted_user)
#
#             # Удаляем пользователя из таблицы users
#             await db.delete(db_user)
#             await db.commit()
#             log.info("User deleted with email: %s", user_email)
#             return deleted_user
#         log.warning("User not found for deletion with email: %s", user_email)
#         return None
#     except SQLAlchemyError as e:
#         log.error("Database error deleting user with email %s: %s", user_email, e)
#         await db.rollback()
#         return None
#     except Exception as e:
#         log.exception("Unexpected error deleting user with email %s: %s", user_email, e)
#         await db.rollback()
#         return None
