import logging
from logging import (
    Formatter,
    Logger,
    StreamHandler,
    basicConfig,
    getLogger,
)
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from typing import Optional

from src.app.core.config import settings


class CustomTextFormatter(Formatter):
    """Кастомный текстовый форматтер для логов с унифицированным контекстом."""

    def format(self, record: logging.LogRecord) -> str:
        # формируем базовое сообщение
        result = super().format(record)

        # добавляем контекст, если он есть
        if hasattr(record, "context_string"):
            result = f"{result} [{record.context_string}]"

        return result


def setup_logging() -> None:
    """
    Настройка логирования на основе конфигурации из settings.
    """

    # создание директории для логов
    log_dir = Path(settings.logging.log_file).parent
    log_dir.mkdir(parents=True, exist_ok=True)

    def _suffix_to_name(default_name: str) -> str:
        """
        Преобразует имя файла для ротации логов.

        :param default_name: Имя файла в формате "base.ext.suffix"
        :return: Имя файла в формате "base.suffix.ext"
        :example: >>> _suffix_to_name("app.log.2024-03-16")
        "app.2024-03-16.log"
        """

        name, ext, suffix = default_name.rsplit(".", 2)
        return f"{name}.{suffix}.{ext}"

    # создаем кастомный текстовый форматтер
    text_formatter = CustomTextFormatter(
        fmt=settings.logging.log_format,
        datefmt=settings.logging.log_date_format,
    )

    # хэндлер для записи в файл с ротацией
    file_handler = TimedRotatingFileHandler(
        filename=settings.logging.log_file,
        when=settings.logging.log_when,
        interval=settings.logging.log_interval,
        backupCount=settings.logging.log_file_backup_count,
        utc=settings.logging.log_utc,
    )
    file_handler.setFormatter(text_formatter)
    file_handler.namer = _suffix_to_name

    # хэндлер для вывода в консоль
    console_handler = StreamHandler()
    console_handler.setFormatter(text_formatter)

    # микрооптимизация
    # отключаем атрибуты, связанные с потоками (thread и threadName)
    logging.logThreads = False

    # отключаем атрибуты, связанные с процессами
    # (processName управляется logMultiprocessing, process — logProcesses)
    logging.logProcesses = False
    # logging.logMultiprocessing = False

    # отключаем атрибут имени асинхронной задачи
    logging.logAsyncioTasks = False

    # настройка корневого логгера
    basicConfig(
        level=settings.logging.log_level_value,
        handlers=([file_handler, console_handler]),
    )

    # отключаем инфо логи от watchfiles (uvicorn hot-reload)
    if settings.env.env == "dev":
        getLogger("watchfiles").setLevel(logging.WARNING)
    else:
        # на проде отключаем логирование подключенных бибилиотек
        getLogger("urllib3").setLevel(logging.ERROR)
        getLogger("taskiq").setLevel(logging.ERROR)
        getLogger("sentry_sdk.errors").setLevel(logging.ERROR)


def get_logger(name: Optional[str] = None) -> Logger:
    """
    Возвращает логгер с указанным именем.
    Если имя не указано, возвращает корневой логгер.
    """

    logger = getLogger(name)

    return logger
