from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.core.config import settings
from src.app.core.exceptions import UserAlreadyExistsError
from src.app.core.logger import get_logger
from src.app.crud.user import create_user
from src.app.crud.user import get_user_by_email, get_user_by_name
from src.app.schemas.user import UserCreate, UserPublic
from src.app.tasks import send_welcome_email
from src.app.core.services.email import send_welcome_email as send_welcome

log = get_logger("user_service")


class UserService:
    """Сервис для работы с пользователями"""

    def __init__(self, session: AsyncSession):
        self.session = session

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

    @staticmethod
    async def _send_welcome_email(user: UserPublic) -> None:
        """Отправляет приветственное письмо пользователю"""

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
