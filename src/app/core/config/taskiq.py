"""Настройки подключения Taskiq к брокеру сообщений."""

from pydantic import AmqpDsn, BaseModel


class TaskiqConfig(BaseModel):
    """Конфигурация AMQP URL для Taskiq."""

    url: AmqpDsn
