from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import aiosmtplib
from aiosmtplib.errors import SMTPException
from fastapi import HTTPException, status
from jinja2 import Environment, FileSystemLoader

from src.app.core.config import settings
from src.app.core.logger import get_logger

log = get_logger("email_services")

env = Environment(loader=FileSystemLoader("src/app/templates"))


async def send_email(
    recipient: str,
    sender: str,
    subject: str,
    template: str,
    context: dict,
) -> None:
    try:
        # Рендеринг HTML-шаблона
        template_obj = env.get_template(template)
        html_content = template_obj.render(**context)

        # Создание многочастного сообщения (для поддержки HTML)
        message = MIMEMultipart("alternative")
        message["From"] = sender
        message["To"] = recipient
        message["Subject"] = subject

        # Добавление HTML-части
        html_part = MIMEText(html_content, "html")
        message.attach(html_part)

        # Отправка письма
        await aiosmtplib.send(
            message,
            recipients=[recipient],
            sender=sender,
            hostname=settings.mail.host,
            port=settings.mail.port,
            username=settings.mail.username,
            password=settings.mail.password,
            use_tls=settings.mail.use_tls,
            timeout=30,
        )
        log.info("Email sent successfully to: %s", recipient)

    except SMTPException as e:
        log.error("Error sending email to %s: %s", recipient, str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "Error sending email",
                "details": {
                    "field": "email",
                    "message": str(e),
                },
            },
        )


async def send_welcome_email(user) -> None:
    """
    Sends a welcome email to a new user.

    This function sends an email to the specified user using the `send_email`
    function. The email contains a welcome message and an unsubscribe link.

    :param user: The user object containing email and username information.
    :type user: User
    :return: None
    """
    await send_email(
        recipient=str(user.email),
        sender=settings.mail.username,
        subject="Добро пожаловать в NutricoreIQ!",
        template="emails/welcome_email.html",
        context={
            "username": user.username,
            "button_link": settings.mail.button_link,
            "unsubscribe_link": settings.mail.unsubscribe_link,
        },
    )
    log.info("Welcome email sent successfully to: %s", user.email)
