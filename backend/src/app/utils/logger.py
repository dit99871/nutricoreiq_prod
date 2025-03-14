import logging
from logging.handlers import RotatingFileHandler
from typing import Optional

from app.core.config import settings


def setup_logging():
    """
    Настройка логирования на основе конфигурации из settings.
    """
    # Форматтер для логов
    formatter = logging.Formatter(settings.logging.log_format)

    # Хэндлер для вывода в консоль
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    # Хэндлер для записи в файл с ротацией
    file_handler = RotatingFileHandler(
        settings.logging.log_file,
        maxBytes=settings.logging.log_file_max_size,
        backupCount=settings.logging.log_file_backup_count,
    )
    file_handler.setFormatter(formatter)

    # Настройка корневого логгера
    logging.basicConfig(
        level=settings.logging.log_level_value,
        handlers=[console_handler, file_handler],
    )


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Возвращает логгер с указанным именем.
    Если имя не указано, возвращает корневой логгер.
    """
    return logging.getLogger(name)
