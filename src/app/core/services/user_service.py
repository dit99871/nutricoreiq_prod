"""Модуль для работы с пользователями"""

from typing import Annotated, Any

from fastapi import HTTPException, status, Depends, Request
from fastapi.responses import ORJSONResponse
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.core import db_helper
from src.app.core.config import settings
from src.app.core.constants import (
    ACCESS_TOKEN_TYPE,
    CREDENTIAL_EXCEPTION,
    TOKEN_TYPE_FIELD,
    REFRESH_TOKEN_TYPE,
)
from src.app.core.exceptions import UserAlreadyExistsError, ExpiredTokenException
from src.app.core.logger import get_logger
from src.app.core.services.jwt_service import get_jwt_from_cookies, get_jwt_payload
from src.app.core.services.email import send_welcome_email as send_welcome
from src.app.core.services.redis import (
    revoke_all_refresh_tokens,
    revoke_refresh_token,
    validate_refresh_jwt,
)
from src.app.core.utils.auth import create_response, verify_password
from src.app.core.repo import (
    create_user,
    get_user_by_email,
    get_user_by_name,
    get_user_by_uid,
    update_user_password,
)
from src.app.core.schemas import UserCreate, UserPublic, PasswordChange
from src.app.core.tasks import send_welcome_email

log = get_logger("user_service")


class UserService:
    """Сервис для работы с пользователями.

    Предоставляет методы для регистрации, аутентификации, входа и выхода из системы
    и управления профилем пользователя.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    @staticmethod
    async def authenticate_user(
        session: AsyncSession,
        username: str,
        password: str,
    ) -> UserPublic:
        """
        Аутентифицирует пользователя по имени и паролю.

        :param session: Асинхронная сессия базы данных.
        :param username: Имя пользователя для аутентификации.
        :param password: Пароль пользователя для проверки.
        :return: Объект UserPublic.
        :raises HTTPException: Если пароль неверный.
        """

        user = await get_user_by_name(session, username)
        if user is None:
            log.error("Пользователя с таким именем не существует в БД")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"message": "Пользователь с таким именем не найден"},
            )

        if not verify_password(password, user.hashed_password):
            log.error(
                "Неверный пароль для пользователя: %s",
                username,
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"message": "Введён неверный пароль"},
            )

        return UserPublic.model_validate(user)

    async def register_user(
        self,
        user_in: UserCreate,
        request: Request,
    ) -> UserPublic:
        """
        Регистрирует нового пользователя

        :param user_in: Данные нового пользователя
        :param request: Объект запроса
        :return: Зарегистрированный пользователь
        :raises UserAlreadyExistsError: Если пользователь с таким email или username уже существует
        :raises HTTPException: При возникновении ошибки при создании пользователя
        """

        client_ip = (request.client.host if request.client else None) or "неизвестен"

        # проверяем существование пользователя по username
        existing_user = await get_user_by_name(self.session, user_in.username)
        if existing_user:
            log.warning(
                "Ошибка регистрации: имя пользователя уже занято: %s, IP: %s",
                user_in.username,
                client_ip,
            )
            raise UserAlreadyExistsError()

        # проверяем существование пользователя по email
        existing_email = await get_user_by_email(self.session, user_in.email)
        if existing_email:
            log.warning(
                "Ошибка регистрации: email уже зарегистрирован: %s, IP: %s",
                user_in.email,
                client_ip,
            )
            raise UserAlreadyExistsError(
                "Пользователь с таким email уже зарегистрирован"
            )

        try:
            # создаем пользователя
            user = await create_user(self.session, user_in)
            log.info(
                "Пользователь успешно зарегистрирован: %s (ID: %s), IP: %s",
                user.email,
                user.id,
                client_ip,
            )

            # отправляем приветственное письмо
            await self._send_welcome_email(user)

            return UserPublic.model_validate(user)

        except Exception as e:
            log.error(
                "Ошибка при регистрации пользователя (email: %s, IP: %s): %s",
                user_in.email,
                client_ip,
                str(e),
                exc_info=True,
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"message": "Произошла ошибка при регистрации"},
            )

    async def login(
        self,
        request: Request,
        session: AsyncSession,
        username: str,
        password: str,
    ) -> ORJSONResponse:
        """
        Осуществляет вход пользователя по имени и паролю.

        :param request: Объект запроса
        :param session: Асинхронная сессия базы данных.
        :param username: Имя пользователя для входа.
        :param password: Пароль пользователя.
        :return: ORJSONResponse для залогиненного пользователя.
        :raises HTTPException:
            - 401: Если имя пользователя или пароль неверны.
            - 500: При возникновении ошибки при аутентификации.
        """

        client_ip = (request.client.host if request.client else None) or "неизвестен"
        log.info(
            "Попытка входа по логину: %s, с IP: %s",
            username,
            client_ip,
        )

        auth_user = await self.authenticate_user(
            session,
            username,
            password,
        )

        return await create_response(auth_user)

    async def logout(
        self,
        request: Request,
        redis: Redis,
        user: UserPublic,
    ) -> ORJSONResponse:
        """
        Выход пользователя из системы и инвалидация refresh токена.

        :param request: Текущий объект запроса.
        :param redis: Redis клиент для инвалидации refresh токена.
        :param user: Аутентифицированный пользователь.
        :return: Ответ с сообщением об успешном выходе.
        :raises ExpiredTokenException: Если refresh токен не найден в cookies запроса.
        """

        if user is None:
            raise ExpiredTokenException()

        refresh_jwt = request.cookies.get(REFRESH_TOKEN_TYPE)
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

        response.delete_cookie(ACCESS_TOKEN_TYPE)
        response.delete_cookie(REFRESH_TOKEN_TYPE)
        response.delete_cookie("redis_session_id")
        response.delete_cookie("csrf_token")

        return response

    @staticmethod
    async def _send_welcome_email(user: UserPublic) -> None:
        """
        Отправляет приветственное письмо пользователю.

        :param user: Объект пользователя, которому отправляется письмо.
        :return: None
        :raises Exception: При ошибке отправки письма.
        """

        try:
            if settings.env.env == "prod":
                # на проде отправляем письмо в фоне через брокер
                await send_welcome_email.kiq(user.email)
            else:
                # в деве отправляем письмо в maildev
                await send_welcome(user)

        except Exception as e:
            log.error(
                "Ошибка при отправке приветственного письма (email: %s): %s",
                user.email,
                str(e),
                exc_info=True,
            )

    async def change_password(
        self,
        request: Request,
        session: AsyncSession,
        user: UserPublic,
        password_data: PasswordChange,
    ) -> ORJSONResponse:
        """
        Изменяет пароль пользователя.

        :param request: Объект текущего запроса
        :param session: Асинхронная сессия базы данных.
        :param user: Объект аутентифицированного пользователя.
        :param password_data: Данные для смены пароля (текущий и новый пароль).
        :return: Ответ об успешной смене пароля.
        :raises HTTPException: Если текущий пароль неверный.
        """

        client_ip = (request.client.host if request.client else None) or "неизвестен"
        log.info(
            "Попытка сменить пароль для пользователя: %s, c IP: %s",
            user.username,
            client_ip,
        )

        authenticated_user = await self.authenticate_user(
            session,
            user.username,
            password_data.current_password,
        )

        await update_user_password(
            session,
            authenticated_user.uid,
            password_data.new_password,
        )
        await revoke_all_refresh_tokens(authenticated_user.uid)

        return await create_response(authenticated_user)

    @staticmethod
    async def get_user_by_access_jwt(
        session: Annotated[AsyncSession, Depends(db_helper.session_getter)],
        token: Annotated[str, Depends(get_jwt_from_cookies)],
    ) -> UserPublic | None:
        """
        Получает текущего аутентифицированного пользователя по access токену.

        Проверяет валидность access токена, извлекает идентификатор пользователя
        и возвращает соответствующий объект пользователя из базы данных.

        :param session: Асинхронная сессия базы данных.
        :param token: Access токен, полученный из cookies.
        :return: Объект UserPublic, если пользователь аутентифицирован.
        :raises HTTPException:
            - 401: Если токен недействителен, истек или пользователь не найден.
            - 404: Если пользователь с указанным идентификатором не существует.
        """

        if token is None:
            return None

        payload: dict = await get_jwt_payload(token)
        token_type: str | None = payload.get(TOKEN_TYPE_FIELD)
        if token_type is None or token_type != ACCESS_TOKEN_TYPE:
            log.error(
                "Такого типа токена %s не существует в payload токена: %s",
                token_type,
                payload,
            )
            raise CREDENTIAL_EXCEPTION

        uid: str | None = payload.get("sub")
        if uid is None:
            log.error("Ошибка получения uid из payload")
            raise CREDENTIAL_EXCEPTION

        user = await get_user_by_uid(session, uid)

        return user

    async def refresh_jwt(
        self,
        request: Request,
        session: AsyncSession,
        redis_service: Redis,
    ) -> ORJSONResponse:
        """
        Получает текущего аутентифицированного пользователя для обновления токенов.

        Проверяет валидность refresh токена, извлекает идентификатор пользователя
        и возвращает соответствующий ответ с обновленными токенами.

        :param request: Объект текущего запроса
        :param session: Асинхронная сессия базы данных.
        :param redis_service: Клиент Redis для проверки валидности токена.
        :return: Объект ORJSONResponse, если пользователь аутентифицирован.
        :raises HTTPException:
            - 401: Если токен недействителен, истек или пользователь не найден.
            - 404: Если пользователь с указанным идентификатором не существует.
        """

        refresh_jwt = await get_jwt_from_cookies(request, REFRESH_TOKEN_TYPE)
        if not refresh_jwt:
            log.error("Refresh токен не найден в куках")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "message": "Ошибка аутентификации. Пожалуйста, войдите заново",
                    "details": {
                        "message": "Refresh token not found in cookies",
                    },
                },
            )

        payload: dict[str, Any] = await get_jwt_payload(refresh_jwt)

        uid: str | None = payload.get("sub")
        if uid is None:
            log.error("Uid пользователя не найден в refresh токене")
            raise CREDENTIAL_EXCEPTION

        if not await validate_refresh_jwt(uid, refresh_jwt, redis_service):
            log.error("Refresh токен невалиден или устарел")
            raise CREDENTIAL_EXCEPTION

        user = await get_user_by_uid(session, uid)

        return await create_response(user)


def get_user_service(
    session: Annotated[AsyncSession, Depends(db_helper.session_getter)],
) -> UserService:
    """
    Фабрика для создания экземпляра UserService.

    :param session: Асинхронная сессия базы данных.
    :return: Экземпляр UserService с переданной сессией.
    """

    return UserService(session=session)
