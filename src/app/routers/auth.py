from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    Response,
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
from src.app.core.redis import get_redis
from src.app.core.services.auth import (
    authenticate_user,
    get_current_auth_user,
    get_current_auth_user_for_refresh,
)
from src.app.core.services.limiter import limiter
from src.app.core.services.user_service import UserService, get_user_service
from src.app.core.utils.auth import create_response
from src.app.schemas.user import PasswordChange, UserCreate, UserPublic

log = get_logger("auth_router")

# алиасы типов зависимостей
db_session = Annotated[AsyncSession, Depends(db_helper.session_getter)]
current_user = Annotated[UserPublic, Depends(get_current_auth_user)]
redis_dependency = Annotated[Redis, Depends(get_redis)]
user_service = Annotated[UserService, Depends(get_user_service)]

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
    user_service: user_service,
) -> UserPublic:
    """
    Регистрирует нового пользователя в базе данных.

    Принимает валидный объект `UserCreate` и регистрирует нового пользователя.
    Если пользователь уже зарегистрирован, вызывает `HTTPException` со статусом 400
    и сообщением об ошибке.

    :param request: Текущий объект запроса.
    :param user_in: Данные пользователя для регистрации.
    :param user_service: Сервис для работы с пользователями, создается автоматически.
    :return: Зарегистрированный пользователь.
    :raises HTTPException: Если пользователь уже зарегистрирован.
    """

    client_host = request.client.host if request.client else None

    try:
        return await user_service.register_user(user_in, client_host)

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
    session: db_session,
) -> Response:
    """
    Аутентифицирует пользователя и возвращает access и refresh токены.

    Принимает логин и пароль, аутентифицирует пользователя и возвращает ответ,
    содержащий access и refresh токены.

    :param request: Текущий объект запроса.
    :param form_data: Данные формы, содержащие имя пользователя и пароль.
    :param session: Текущая сессия базы данных.
    :return: Ответ, содержащий access и refresh токены.
    """

    user = await authenticate_user(
        session,
        form_data.username,
        form_data.password,
    )
    response = await create_response(user)

    return response


@router.post("/logout")
async def logout(
    request: Request,
    user: current_user,
    redis: redis_dependency,
    user_service: user_service,
) -> Response:
    """
    Выход пользователя из системы и инвалидация refresh токена.

    :param request: Текущий объект запроса.
    :param user: Аутентифицированный пользователь.
    :param redis: Redis клиент для инвалидации refresh токена.
    :param user_service: Сервис для работы с пользователями.
    :return: Ответ с сообщением об успешном выходе.
    """

    return await user_service.logout(request, redis, user)


@router.post(
    "/refresh",
    response_model_exclude_none=True,
)
async def refresh_token(
    request: Request,
    session: db_session,
    redis: redis_dependency,
) -> Response:
    """
    Обновляет access и refresh токены для пользователя.

    Принимает refresh токен из cookies запроса и возвращает новый access и refresh токен,
    если токен валиден. Если токен недействителен или истек, вызывает исключение 401.

    :param request: Текущий объект запроса.
    :param session: Текущая сессия базы данных.
    :param redis: Redis клиент для валидации refresh токена.
    :return: Ответ с новыми access и refresh токенами.
    :raises HTTPException: Если refresh токен не найден или недействителен.
    """

    refresh_jwt = request.cookies.get("refresh_token")
    if not refresh_jwt:
        log.error("Refresh token not found in cookies")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "message": "Ошибка аутентификации. Пожалуйста, войдите заново",
                "details": {
                    "message": "Refresh token not found in cookies",
                },
            },
        )

    user = await get_current_auth_user_for_refresh(refresh_jwt, session, redis)
    response = await create_response(user)

    return response


@router.post("/password/change")
@limiter.limit(settings.rate_limit.password_change_limit)
async def change_password(
    password_data: PasswordChange,
    request: Request,
    user: current_user,
    session: db_session,
    user_service: user_service,
) -> Response:
    """
    Изменяет пароль аутентифицированного пользователя.

    Принимает текущий и новый пароль, проверяет их валидность и обновляет пароль
    пользователя в системе. Требует аутентификации.

    :param password_data: Данные для смены пароля (текущий и новый пароль)
    :param request: Объект запроса FastAPI
    :param user: Текущий аутентифицированный пользователь
    :param session: Сессия базы данных
    :param user_service: Сервис для работы с пользователями
    :return: Ответ с результатом операции
    :raises ExpiredTokenException: Если пользователь не аутентифицирован
    :raises HTTPException: При ошибках валидации или несоответствии текущего пароля
    """

    if user is None:
        raise ExpiredTokenException()

    return await user_service.change_password(session, user, password_data)
