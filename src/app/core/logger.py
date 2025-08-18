import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import json
from typing import Optional
from datetime import datetime

from src.app.core.config import settings


class JsonFormatter(logging.Formatter):
    """Форматирует логи в JSON для Loki."""

    def format(self, record):
        log_entry = {
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
            "level": record.levelname,
            "message": record.getMessage(),
            "source": "app",
            "name": record.name,
            "lineno": record.lineno,
        }
        return json.dumps(log_entry)


def setup_logging() -> None:
    """
    Настройка логирования на основе конфигурации из settings.
    Логи записываются в JSON для Loki и в текстовом формате для консоли.
    """
    # Создание директории для логов
    log_dir = Path(settings.logging.log_file).parent
    log_dir.mkdir(parents=True, exist_ok=True)

    # JSON форматтер для файла
    json_formatter = JsonFormatter()

    # Текстовый форматтер для консоли
    text_formatter = logging.Formatter(
        fmt=settings.logging.log_format,
        datefmt=settings.logging.log_date_format,
    )

    # Хэндлер для записи в файл с ротацией
    file_handler = RotatingFileHandler(
        settings.logging.log_file,
        maxBytes=settings.logging.log_file_max_size,
        backupCount=settings.logging.log_file_backup_count,
    )
    file_handler.setFormatter(
        json_formatter
        if settings.logging.log_stage == "PROD"
        else text_formatter,
    )

    # Хэндлер для вывода в консоль
    # console_handler = logging.StreamHandler()
    # console_handler.setFormatter(text_formatter)

    # Настройка корневого логгера
    logging.basicConfig(
        level=settings.logging.log_level_value,
        handlers=[
            file_handler,
            # console_handler,
        ],
    )


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Возвращает логгер с указанным именем.
    Если имя не указано, возвращает корневой логгер.
    """
    return logging.getLogger(name)
