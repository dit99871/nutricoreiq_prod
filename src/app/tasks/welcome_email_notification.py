from typing import Annotated

from pydantic import EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from taskiq import TaskiqDepends

from src.app.core.logger import get_logger
from src.app.core import broker
from src.app.crud.user import get_user_by_email
from src.app.db import db_helper
from src.app.services.email import send_welcome_email as send_welcome

log = get_logger("email_tasks")


@broker.task
async def send_welcome_email(
    user_email: EmailStr,
    session: Annotated[AsyncSession, TaskiqDepends(db_helper.session_getter)],
) -> None:
    user = await get_user_by_email(session, user_email)
    log.info("Sending welcome email to: %s", user.email)

    await send_welcome(user)
