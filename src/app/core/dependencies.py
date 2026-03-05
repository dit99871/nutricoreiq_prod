"""Общие зависимости для роутеров"""

from typing import Annotated

from fastapi import Depends
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.core import db_helper
from src.app.core.redis import get_redis_service
from src.app.core.services.user_service import UserService, get_user_service
from src.app.core.schemas.user import UserPublic

# общие зависимости
db_session_dep = Annotated[AsyncSession, Depends(db_helper.session_getter)]
redis_service_dep = Annotated[Redis, Depends(get_redis_service)]
user_service_dep = Annotated[UserService, Depends(get_user_service)]

# зависимость для получения текущего пользователя
current_user_dep = Annotated[
    UserPublic, Depends(user_service_dep.get_user_by_access_jwt)
]
