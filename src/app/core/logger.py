import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

from src.app.core.config import settings


def setup_logging() -> None:
    """
    Настройка логирования на основе конфигурации из settings.
    """
    # Создание директории для логов
    log_dir = Path(settings.logging.log_file).parent
    log_dir.mkdir(parents=True, exist_ok=True)

    formatter = logging.Formatter(
        fmt=settings.logging.log_format,
        datefmt=settings.logging.log_date_format,
    )

    # Хэндлер для записи в файл с ротацией
    file_handler = RotatingFileHandler(
        settings.logging.log_file,
        maxBytes=settings.logging.log_file_max_size,
        backupCount=settings.logging.log_file_backup_count,
    )

    file_handler.setFormatter(formatter)

    # Хэндлер для вывода в консоль
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    # Настройка корневого логгера
    logging.basicConfig(
        level=settings.logging.log_level_value,
        handlers=[file_handler, console_handler],
    )


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Возвращает логгер с указанным именем.
    Если имя не указано, возвращает корневой логгер.
    """
    return logging.getLogger(name)
