from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import aiosmtplib
from aiosmtplib.errors import SMTPException
from jinja2 import Environment, FileSystemLoader

from src.app.core.config import settings
from src.app.core.constants import BASE_DIR
from src.app.core.logger import get_logger
from src.app.core.schemas.user import UserPublic

log = get_logger("email_services")

env = Environment(loader=FileSystemLoader(str((BASE_DIR / "templates").resolve())))


async def send_email(
    recipient: str,
    sender: str,
    subject: str,
    template: str,
    context: dict,
) -> None:
    """
    Asynchronously sends an email to the recipient using the given template.

    The template will be rendered with the given context dictionary.
    The rendered HTML content is then sent as a MIME message with an
    "alternative" type, which allows the recipient's email client to decide
    whether to render the HTML or not.

    :param recipient: The recipient's email address
    :param sender: The sender's email address
    :param subject: The email's subject
    :param template: The name of the template to use (should be in the
                     templates directory)
    :param context: The dictionary of values to use when rendering the template
    :raises Exception: If there is an error sending the email
    """

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

        # Подготовка аргументов для SMTP: без AUTH, если не заданы и логин, и пароль
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
        log.info("Email sent successfully to: %s", recipient)

    except SMTPException as e:
        log.error("Error sending email to %s: %s", recipient, str(e))
        raise Exception(f"Failed to send email to {recipient}: {str(e)}")


async def send_welcome_email(user: UserPublic) -> None:
    """
    Sends a welcome email to a new user.

    This function sends an email to the specified user using the `send_email`
    function. The email contains a welcome message and an unsubscribe link.

    :param user: The user object containing email and username information.
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
