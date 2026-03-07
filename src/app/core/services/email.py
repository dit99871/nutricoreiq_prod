from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import aiosmtplib
from aiosmtplib.errors import SMTPException
from jinja2 import Environment, FileSystemLoader

from src.app.core.config import settings
from src.app.core.constants import BASE_DIR
from src.app.core.logger import get_logger
from src.app.core.utils.security import mask_email
from src.app.core.schemas.user import UserPublic

log = get_logger("email_service")

env = Environment(loader=FileSystemLoader(str((BASE_DIR / "templates").resolve())))


async def send_email(
    recipient: str,
    sender: str,
    subject: str,
    template: str,
    context: dict,
) -> None:
    """
    Асинхронно отправляет email получателю используя указанный шаблон.

    Шаблон будет отрендерен с использованием переданного словаря контекста.
    Отрендеренный HTML-контент затем отправляется как MIME-сообщение с
    типом "alternative", что позволяет почтовому клиенту получателя решить,
    рендерить HTML или нет.

    :param recipient: Email адрес получателя
    :param sender: Email адрес отправителя
    :param subject: Тема письма
    :param template: Имя шаблона для использования (должен быть в
                     директории templates)
    :param context: Словарь значений для использования при рендеринге шаблона
    :raises Exception: Если произошла ошибка при отправке email
    """

    try:
        # рендеринг хтмл-шаблона
        template_obj = env.get_template(template)
        html_content = template_obj.render(**context)

        # создание сообщения (для поддержки хтмл)
        message = MIMEMultipart("alternative")
        message["From"] = sender
        message["To"] = recipient
        message["Subject"] = subject

        # добавление хтмл-части
        html_part = MIMEText(html_content, "html")
        message.attach(html_part)

        # подготовка аргументов для smtp: без auth, если не заданы и логин, и пароль
        send_kwargs = dict(
            recipients=[recipient],
            sender=sender,
            hostname=settings.mail.host,
            port=settings.mail.port,
            use_tls=settings.mail.use_tls,
            timeout=60,
        )
        if getattr(settings.mail, "username", None) and getattr(
            settings.mail, "password", None
        ):
            send_kwargs["username"] = settings.mail.username
            send_kwargs["password"] = settings.mail.password

        # Отправка письма
        await aiosmtplib.send(
            message,
            **send_kwargs,
        )
        log.info("Email sent successfully to: %s", mask_email(recipient))

    except SMTPException as e:
        log.error("Error sending email to %s: %s", mask_email(recipient), str(e))
        raise Exception(f"Failed to send email to {mask_email(recipient)}: {str(e)}")


async def send_welcome_email(user: UserPublic) -> None:
    """
    Отправляет приветственное письмо новому пользователю.

    Эта функция отправляет email указанному пользователю используя функцию `send_email`.
    Письмо содержит приветственное сообщение и ссылку для отписки.

    :param user: Объект пользователя содержащий email и информацию об имени пользователя.
    :return: None
    """

    await send_email(
        recipient=user.email,
        sender=settings.mail.username,
        subject="Добро пожаловать в NutricoreIQ!",
        template="emails/welcome_email.html",
        context={
            "username": user.username,
            "button_link": settings.mail.button_link,
            "unsubscribe_link": settings.mail.unsubscribe_link,
        },
    )
    log.info("Welcome email sent successfully to: %s", mask_email(user.email))
