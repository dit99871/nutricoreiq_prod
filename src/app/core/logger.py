import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

from src.app.core.config import settings


class CustomTextFormatter(logging.Formatter):
    """Кастомный текстовый форматтер для логов с унифицированным контекстом."""

    def format(self, record):
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

    # создаем кастомный текстовый форматтер
    text_formatter = CustomTextFormatter(
        fmt=settings.logging.log_format,
        datefmt=settings.logging.log_date_format,
    )

    # хэндлер для записи в файл с ротацией
    file_handler = RotatingFileHandler(
        settings.logging.log_file,
        maxBytes=settings.logging.log_file_max_size,
        backupCount=settings.logging.log_file_backup_count,
    )
    file_handler.setFormatter(text_formatter)

    # хэндлер для вывода в консоль
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(text_formatter)

    # настройка корневого логгера
    logging.basicConfig(
        level=settings.logging.log_level_value,
        handlers=[
            file_handler,
            console_handler,
        ],
    )


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Возвращает логгер с указанным именем.
    Если имя не указано, возвращает корневой логгер.
    """

    logger = logging.getLogger(name)

    return logger
