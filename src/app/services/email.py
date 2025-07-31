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
            port=settings.mail.port,
            hostname=settings.mail.host,
            username=settings.mail.username,
            password=settings.mail.password,
            use_tls=settings.mail.use_ssl,
            timeout=30,
        )
        log.info("Email sent successfully to: %s", recipient)
    except SMTPException as e:
        log.error("Error sending email to %s: %s", recipient, str(e))
        raise Exception(f"Failed to send email to {recipient}: {str(e)}")


async def send_welcome_email(user) -> None:
    await send_email(
        recipient=str(user.email),
        sender=settings.mail.username,
        subject="Добро пожаловать в NutricoreIQ!",
        template="emails/welcome_email.html",
        context={
            "username": user.username,
            "unsubscribe_link": "https://nutricoreiq.ru/unsubscribe",
        },
    )
    log.info("Welcome email sent successfully to: %s", user.email)
