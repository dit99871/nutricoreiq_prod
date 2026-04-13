"""Настройки логирования приложения."""

import logging
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from src.app.core.constants import BASE_DIR


class LoggingConfig(BaseSettings):
    """Конфигурация логирования, читаемая из переменных окружения."""

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        case_sensitive=False,
        env_nested_delimiter="__",
        env_prefix="LOGGING__",
        extra="ignore",
    )

    log_level: Literal[
        "DEBUG",
        "INFO",
        "WARNING",
        "ERROR",
        "CRITICAL",
    ] = "INFO"
    log_format: str = Field(
        default="[%(asctime)s.%(msecs)03d] %(name)-20s:%(lineno)3d %(levelname)7s - %(message)s",
        description="Формат для логов приложения",
    )
    log_taskiq_format: str = Field(
        default="[%(asctime)s.%(msecs)03d] [%(processName)s] %(module)s:%(lineno)d %(levelname)s - %(message)s",
        description="Формат для логов TaskIQ worker",
    )
    log_date_format: str = Field(
        default="%Y-%m-%d %H:%M:%S",
        description="Формат даты для логов",
    )
    log_file: str = Field(
        default=str(BASE_DIR / "logs" / "app.log"),
        description="Путь к файлу логов",
    )
    log_interval: int = Field(
        default=1,
        description="Интервал ротации логов",
    )
    log_file_backup_count: int = Field(
        default=7,
        description="Количество резервных копий логов для хранения",
    )
    log_when: str = Field(
        default="MIDNIGHT",
        description="Когда происходит ротация логов",
    )
    log_utc: bool = Field(
        default=True,
        description="Ротация логов в UTC",
    )

    @property
    def log_level_value(self) -> int:
        """Возвращает числовое значение уровня логирования."""

        return logging.getLevelNamesMapping()[self.log_level.upper()]
