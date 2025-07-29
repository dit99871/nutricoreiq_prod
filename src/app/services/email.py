from email.message import EmailMessage

import aiosmtplib
from aiosmtplib.errors import SMTPException
from fastapi import HTTPException, status

from src.app.core.config import settings
from src.app.core.logger import get_logger
from src.app.crud.user import get_user_by_email
from src.app.db import db_helper

log = get_logger("email_services")


async def send_email(
    recipient: str,
    sender: str,
    subject: str,
    body: str,
) -> None:
    message = EmailMessage()
    message["From"] = sender
    message["To"] = recipient
    message["Subject"] = subject
    message.set_content(body)

    try:
        await aiosmtplib.send(
            message,
            recipients=[recipient],
            sender=sender,
            port=settings.mail.port,
            hostname=settings.mail.host,
            username=settings.mail.username,
            password=settings.mail.password,
        )
    except SMTPException as e:
        log.error(
            "Error sending email: %s",
            str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "Error sending email",
                "details": {
                    "field": "email",
                    "message": "Error sending email",
                },
            },
        )


async def send_welcome_email(user_email) -> None:
    """
    Sends a welcome email to a user.

    :param user_email: The email address of the user to send the email to.
    """
    async with db_helper.session_getter() as session:
        user = await get_user_by_email(session, user_email)

    await send_email(
        recipient=str(user.email),
        sender=settings.mail.username,
        subject="Добро пожаловать в NutricoreIQ!",
        body=f"{user.username}, добро пожаловать в NutricoreIQ!",
    )

    log.info("Welcome email sent successfully to: %s", user.email)
