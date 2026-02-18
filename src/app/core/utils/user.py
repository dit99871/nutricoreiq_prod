"""Утилиты для работы с текущим пользователем"""

from typing import Annotated, Optional

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.core import db_helper
from src.app.core.schemas.user import UserPublic


async def get_user_from_request(
    request: Request, session: AsyncSession
) -> Optional[UserPublic]:
    """
    Получает пользователя из JWT токена в cookies.

    Безопасно возвращает None если:
    - Токен отсутствует в cookies
    - Токен невалидный или просроченный
    - Пользователь не найден в БД

    :param request: Объект запроса FastAPI
    :param session: Сессия базы данных
    :return: Объект UserPublic или None
    """

    try:
        from src.app.core.services.jwt_service import (
            get_jwt_from_cookies,
            get_jwt_payload,
        )
        from src.app.core.constants import TOKEN_TYPE_FIELD, ACCESS_TOKEN_TYPE
        from src.app.core.repo.user import get_user_by_uid

        # Получаем токен из cookies
        token = await get_jwt_from_cookies(request)
        if not token:
            return None

        # Валидируем и расшифровываем токен
        payload = await get_jwt_payload(token)
        if payload.get(TOKEN_TYPE_FIELD) != ACCESS_TOKEN_TYPE:
            return None

        # Получаем ID пользователя
        uid = payload.get("sub")
        if not uid:
            return None

        # Находим пользователя в БД
        return await get_user_by_uid(session, uid)

    except Exception:
        # Любая ошибка означает что пользователь не авторизован
        return None


def optional_current_user():
    """
    Создает опциональную зависимость для получения текущего пользователя.

    Возвращает:
    - UserPublic если пользователь авторизован
    - None если пользователь не авторизован или токен невалидный

    Использование:
    ```python
    @router.get("/some-endpoint")
    async def some_endpoint(user: Optional[UserPublic] = Depends(optional_current_user())):
        if user:
            # авторизованный пользователь
            pass
        else:
            # неавторизованный пользователь
            pass
    ```
    """

    async def dependency(
        request: Request,
        session: Annotated[AsyncSession, Depends(db_helper.session_getter)],
    ) -> Optional[UserPublic]:

        return await get_user_from_request(request, session)

    return dependency
