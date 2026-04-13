"""Настройки SMTP для отправки писем."""

from pydantic import BaseModel


class SMTPConfig(BaseModel):
    """Конфигурация подключения к SMTP серверу и ссылок в письмах."""

    host: str
    port: int
    button_link: str
    unsubscribe_link: str
    username: str | None = None
    password: str | None = None
    use_tls: bool | None = None
