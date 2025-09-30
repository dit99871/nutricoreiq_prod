from typing import Optional, Annotated

from fastapi import HTTPException, status, Depends, Request
from fastapi.responses import ORJSONResponse
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.core import db_helper
from src.app.core.config import settings
from src.app.core.constants import CREDENTIAL_EXCEPTION
from src.app.core.exceptions import UserAlreadyExistsError, ExpiredTokenException
from src.app.core.logger import get_logger
from src.app.core.services.auth import (
    get_access_token_from_cookies,
    get_current_access_token_payload,
)
from src.app.core.services.jwt_service import decode_jwt
from src.app.core.services.redis import (
    revoke_refresh_token,
    revoke_all_refresh_tokens,
    validate_refresh_jwt,
)
from src.app.core.utils.auth import create_response, verify_password
from src.app.crud.user import create_user, update_user_password, get_user_by_uid
from src.app.crud.user import get_user_by_email, get_user_by_name

from src.app.schemas.user import UserCreate, UserPublic, PasswordChange
from src.app.tasks import send_welcome_email
from src.app.core.services.email import send_welcome_email as send_welcome

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
        client_ip: Optional[str] = None,
    ) -> UserPublic:
        """
        Регистрирует нового пользователя

        :param user_in: Данные нового пользователя
        :param client_ip: IP-адрес клиента для логирования
        :return: Зарегистрированный пользователь
        :raises UserAlreadyExistsError: Если пользователь с таким email или username уже существует
        :raises HTTPException: При возникновении ошибки при создании пользователя
        """

        client_ip = client_ip or "неизвестен"

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
        session: AsyncSession,
        username: str,
        password: str,
    ) -> UserPublic:
        """
        Аутентифицирует пользователя по имени пользователя и паролю.

        :param session: Асинхронная сессия базы данных.
        :param username: Имя пользователя для входа.
        :param password: Пароль пользователя.
        :return: UserPublic-схема.
        :raises HTTPException:
            - 401: Если имя пользователя или пароль неверны.
            - 500: При возникновении ошибки при аутентификации.
        """

        return await self.authenticate_user(
            session,
            username,
            password,
        )

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
        session: AsyncSession,
        user: UserPublic,
        password_data: PasswordChange,
    ) -> ORJSONResponse:
        """
        Изменяет пароль пользователя.

        :param session: Асинхронная сессия базы данных.
        :param user: Объект аутентифицированного пользователя.
        :param password_data: Данные для смены пароля (текущий и новый пароль).
        :return: Ответ об успешной смене пароля.
        :raises HTTPException: Если текущий пароль неверный.
        """

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

    async def get_current_auth_user(
        self,
        session: Annotated[AsyncSession, Depends(db_helper.session_getter)],
        token: Annotated[str, Depends(get_access_token_from_cookies)],
    ) -> UserPublic | None:
        """
        Получает текущего аутентифицированного пользователя на основе access токена.

        Извлекает и проверяет access токен из куки запроса, затем находит
        соответствующего пользователя в базе данных.

        :param session: Асинхронная сессия базы данных.
        :param token: Access токен, извлеченный из куки запроса.
        :return: Объект UserPublic, если пользователь аутентифицирован, иначе None.
        :raises HTTPException:
            - 401: Если токен недействителен или истек.
            - 404: Если пользователь не найден.
        """

        if token is None:
            return None

        payload: dict = get_current_access_token_payload(token)
        uid: str | None = payload.get("sub")
        if uid is None:
            log.error("Ошибка получения uid из payload")
            raise CREDENTIAL_EXCEPTION

        user = await get_user_by_uid(session, uid)

        return user

    async def get_current_auth_user_for_refresh(
        self,
        token: str,
        session: AsyncSession,
        redis: Redis,
    ) -> UserPublic:
        """
        Получает текущего аутентифицированного пользователя для обновления токенов.

        Проверяет валидность refresh токена, извлекает идентификатор пользователя
        и возвращает соответствующий объект пользователя из базы данных.

        :param token: Refresh токен из cookies запроса.
        :param session: Асинхронная сессия базы данных.
        :param redis: Клиент Redis для проверки валидности токена.
        :return: Объект UserPublic, если пользователь аутентифицирован.
        :raises HTTPException:
            - 401: Если токен недействителен, истек или пользователь не найден.
            - 404: Если пользователь с указанным идентификатором не существует.
        """

        payload = decode_jwt(token)
        if payload is None:
            log.error("Ошибка декодирования refresh токена")
            raise CREDENTIAL_EXCEPTION

        uid: str | None = payload.get("sub")
        if uid is None:
            log.error("id пользователя не найден в refresh токене")
            raise CREDENTIAL_EXCEPTION

        if not await validate_refresh_jwt(uid, token, redis):
            log.error("refresh токен невалиден или устарел")
            raise CREDENTIAL_EXCEPTION

        user = await get_user_by_uid(session, uid)

        return user


def get_user_service(
    session: Annotated[AsyncSession, Depends(db_helper.session_getter)],
) -> UserService:
    """
    Фабрика для создания экземпляра UserService.

    :param session: Асинхронная сессия базы данных.
    :return: Экземпляр UserService с переданной сессией.
    """

    return UserService(session=session)
