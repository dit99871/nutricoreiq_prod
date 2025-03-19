from logging import Logger
from typing import Optional

from models import User


async def log_user_result(
    user: Optional[User],
    logger: Logger,
    success_message: str,
    not_found_message: str,
) -> Optional[User]:
    """Обрабатывает результат запроса пользователя и логирует сообщение."""
    if user:
        logger.info(success_message)
    else:
        logger.warning(not_found_message)
    return user
