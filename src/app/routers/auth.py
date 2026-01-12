"""Модуль с ручками для аутентификации"""

from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    status,
)
from fastapi.responses import ORJSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.core import db_helper
from src.app.core.config import settings
from src.app.core.exceptions import ExpiredTokenException, UserAlreadyExistsError
from src.app.core.logger import get_logger
from src.app.core.redis import get_redis_service
from src.app.core.services.limiter import limiter
from src.app.core.services.user_service import UserService, get_user_service
from src.app.core.schemas import PasswordChange, UserCreate, UserPublic

log = get_logger("auth_router")

# алиасы типов зависимостей
user_service_dep = Annotated[UserService, Depends(get_user_service)]
db_session_dep = Annotated[AsyncSession, Depends(db_helper.session_getter)]
current_user_dep = Annotated[
    UserPublic, Depends(user_service_dep.get_user_by_access_jwt)
]
redis_service_dep = Annotated[Redis, Depends(get_redis_service)]

router = APIRouter(
    tags=["Authentication"],
    default_response_class=ORJSONResponse,
)


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit(settings.rate_limit.register_limit)
async def register_user(
    request: Request,
    user_in: UserCreate,
    user_service: user_service_dep,
) -> UserPublic:
    """
    Регистрирует нового пользователя в базе данных.

    Принимает валидный объект `UserCreate` и регистрирует нового пользователя.
    Если пользователь уже зарегистрирован, вызывает `HTTPException` со статусом 400
    и сообщением об ошибке.

    :param request: Объект текущего запроса.
    :param user_in: Данные пользователя для регистрации.
    :param user_service: Сервис для работы с пользователями, создается автоматически.
    :return: Зарегистрированный пользователь.
    :raises HTTPException: Если пользователь уже зарегистрирован.
    """

    try:
        return await user_service.register_user(user_in=user_in, request=request)

    except UserAlreadyExistsError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": str(e)},
        )


@router.post("/login")
@limiter.limit(settings.rate_limit.login_limit)
async def login(
    request: Request,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: db_session_dep,
    user_service: user_service_dep,
) -> ORJSONResponse:
    """
    Аутентифицирует пользователя и возвращает response с access и refresh токенами.

    Принимает имя пользователя и пароль, проверяет их валидность и возвращает
    access и refresh токены в случае успешной аутентификации. Использует OAuth2
    схему аутентификации.

    :param request: Объект текущего запроса.
    :param form_data: Данные формы, содержащие имя пользователя и пароль.
    :param session: Текущая сессия базы данных.
    :param user_service: Сервис для работы с пользователями.
    :return: Response с access и refresh токенами.
    :raises HTTPException:
        - 401: Если имя пользователя или пароль неверны.
        - 500: При возникновении ошибки при аутентификации.
    """

    return await user_service.login(
        request=request,
        session=session,
        username=form_data.username,
        password=form_data.password,
    )


@router.post("/logout")
async def logout(
    request: Request,
    user: current_user_dep,
    redis_service: redis_service_dep,
    user_service: user_service_dep,
) -> ORJSONResponse:
    """
    Выход пользователя из системы и инвалидация refresh токена.

    :param request: Объект текущего запроса.
    :param user: Аутентифицированный пользователь.
    :param redis_service: Redis клиент для инвалидации refresh токена.
    :param user_service: Сервис для работы с пользователями.
    :return: Ответ с сообщением об успешном выходе.
    """

    return await user_service.logout(request, redis_service, user)


@router.post(
    "/refresh",
    response_model_exclude_none=True,
)
async def refresh_token(
    request: Request,
    session: db_session_dep,
    redis_service: redis_service_dep,
    user_service: user_service_dep,
) -> ORJSONResponse:
    """
    Обновляет access и refresh токены пользователя.

    Принимает валидный refresh токен и возвращает новую пару access и refresh токенов.
    Старый refresh токен помечается как использованный в Redis.

    :param request: Объект текущего запроса.
    :param session: Текущая сессия базы данных.
    :param redis_service: Redis клиент для работы с refresh токенами.
    :param user_service: Сервис для работы с пользователями.
    :return: Response с новыми access и refresh токенами.
    :raises HTTPException:
        - 401: Если refresh токен невалидный или истек.
        - 400: Если токен не передан или имеет неверный формат.
    """

    return await user_service.refresh_jwt(
        request=request,
        session=session,
        redis_service=redis_service,
    )


@router.post("/password/change")
@limiter.limit(settings.rate_limit.password_change_limit)
async def change_password(
    password_data: PasswordChange,
    request: Request,
    user: current_user_dep,
    session: db_session_dep,
    user_service: user_service_dep,
) -> ORJSONResponse:
    """
    Изменяет пароль аутентифицированного пользователя.

    Принимает текущий и новый пароль, проверяет их валидность и обновляет пароль
    пользователя в системе. Требует аутентификации.

    :param password_data: Данные для смены пароля (текущий и новый пароль)
    :param request: Объект текущего запроса
    :param user: Текущий аутентифицированный пользователь
    :param session: Сессия базы данных
    :param user_service: Сервис для работы с пользователями
    :return: Ответ с результатом операции
    :raises ExpiredTokenException: Если пользователь не аутентифицирован
    :raises HTTPException: При ошибках валидации или несоответствии текущего пароля
    """

    if user is None:
        raise ExpiredTokenException()

    return await user_service.change_password(
        request=request,
        session=session,
        user=user,
        password_data=password_data,
    )
