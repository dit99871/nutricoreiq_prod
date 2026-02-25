import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

from src.app.core.config import settings


class CustomTextFormatter(logging.Formatter):
    """Кастомный текстовый форматтер для логов."""

    def format(self, record):
        # формируем базовое сообщение
        result = super().format(record)

        # добавляем дополнительные поля, если они есть
        extra_info = []
        if hasattr(record, "request_id"):
            extra_info.append(f"request_id={record.request_id}")

            # добавляем дополнительные поля, которые могут быть полезны
            for field in [
                "method",
                "url",
                "client_ip",
                "user_agent",
                "status_code",
                "process_time_ms",
            ]:
                if hasattr(record, field):
                    value = getattr(record, field)
                    if value is not None:
                        extra_info.append(f"{field}={value}")

        if extra_info:
            result = f"{result} [{' | '.join(extra_info)}]"

        return result


def setup_logging() -> None:
    """
    Настройка логирования на основе конфигурации из settings.
    Логи записываются в JSON для Loki и в текстовом формате для консоли.
    """

    # Проверяем, что логирование еще не настроено
    root_logger = logging.getLogger()
    if root_logger.handlers:
        # Логгеры уже настроены, выходим
        return

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

    return logging.getLogger(name)
