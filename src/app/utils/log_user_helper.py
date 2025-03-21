from logging import Logger


async def log_user_result(
    user,
    logger: Logger,
    success_message: str,
    not_found_message: str,
):
    """Обрабатывает результат запроса пользователя и логирует сообщение."""
    if user:
        logger.info(success_message)
    else:
        logger.warning(not_found_message)
    return user
