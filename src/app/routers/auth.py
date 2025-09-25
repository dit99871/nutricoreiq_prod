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
from src.app.core.exceptions import ExpiredTokenException
from src.app.core.logger import get_logger
from src.app.core.redis import get_redis
from src.app.core.services.auth import (
    authenticate_user,
    get_current_auth_user,
    get_current_auth_user_for_refresh,
    update_password,
)
from src.app.core.services.email import send_welcome_email as send_welcome
from src.app.core.services.limiter import limiter
from src.app.core.services.redis import revoke_refresh_token
from src.app.core.utils.auth import create_response
from src.app.crud.user import create_user, get_user_by_email
from src.app.schemas.user import PasswordChange, UserCreate, UserPublic
from src.app.tasks import send_welcome_email

log = get_logger("auth_router")

# алиасы типов зависимостей
db_session = Annotated[AsyncSession, Depends(db_helper.session_getter)]
current_user = Annotated[UserPublic, Depends(get_current_auth_user)]
redis_dependency = Annotated[Redis, Depends(get_redis)]

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
    session: db_session,
) -> UserPublic:
    """
    Регистрирует нового пользователя в базе данных.

    Принимает валидный объект `UserCreate` и регистрирует нового пользователя.
    Если пользователь уже зарегистрирован, вызывает `HTTPException` со статусом 400
    и сообщением об ошибке.

    :param request: Текущий объект запроса.
    :param user_in: Данные пользователя для регистрации.
    :param session: Сессия базы данных для выполнения запроса.
    :return: Зарегистрированный пользователь.
    :raises HTTPException: Если пользователь уже зарегистрирован.
    """

    db_user = await get_user_by_email(session, user_in.email)

    if db_user:
        log.error(
            "Registration failed: Email already registered: %s",
            user_in.email,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": "Пользователь с таким email уже зарегистрирован",
            },
        )
    user = await create_user(session, user_in)
    log.info("User registered successfully: %s", user.email)

    if settings.env.env == "prod":
        # на проде отправляем письмо в фоне через брокер
        await send_welcome_email.kiq(user.email)
    else:
        # в dev отправляем письмо в maildev
        await send_welcome(user)

    # возвращаем только публичные данные, без пароля
    return UserPublic.model_validate(user)


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
) -> Response:
    """
    Выход пользователя из системы и инвалидация refresh токена.

    Этот эндпоинт выполняет выход пользователя, инвалидирует его refresh токен
    и удаляет access и refresh токены из cookies запроса.

    :param request: Текущий объект запроса.
    :param user: Аутентифицированный пользователь.
    :param redis: Redis клиент для инвалидации refresh токена.
    :return: Ответ с сообщением об успешном выходе.
    :raises HTTPException: Если refresh токен не найден в cookies запроса.
    """

    if user is None:
        raise ExpiredTokenException()
    refresh_jwt = request.cookies.get("refresh_token")

    if not refresh_jwt:
        log.error("Refresh token not found in cookies")
        raise ExpiredTokenException()

    await revoke_refresh_token(user.uid, refresh_jwt, redis)

    session_id = request.cookies.get("redis_session_id")
    if session_id:
        await redis.delete(f"redis_session:{session_id}")

    response = ORJSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "Successfully logged out"},
    )

    response.delete_cookie("refresh_token")
    response.delete_cookie("access_token")
    response.delete_cookie("redis_session_id")
    response.delete_cookie("csrf_token")

    return response


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
) -> Response:
    """
    Изменяет пароль аутентифицированного пользователя.

    Принимает старый и новый пароль, проверяет старый пароль и,
    если он верный, изменяет его на новый.

    :param password_data: Новый и текущий пароли.
    :param request: Текущий объект запроса.
    :param user: Аутентифицированный пользователь.
    :param session: Текущая сессия базы данных.
    :return: Ответ с новыми access и refresh токенами.
    :raises HTTPException: Если текущий пароль неверен.
    :raises HTTPException: При возникновении непредвиденной ошибки.
    """

    if user is None:
        raise ExpiredTokenException()

    authenticated_user = await authenticate_user(
        session, user.username, password_data.current_password
    )

    return await update_password(
        authenticated_user, session, password_data.new_password
    )
