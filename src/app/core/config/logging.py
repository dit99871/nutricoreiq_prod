import logging
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from src.app.core.constants import BASE_DIR


class LoggingConfig(BaseSettings):
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
        default="[%(asctime)s.%(msecs)03d] %(name)s:%(lineno)d %(levelname)s - %(message)s",
        description="Format for application logs"
    )
    log_taskiq_format: str = Field(
        default="[%(asctime)s.%(msecs)03d] [%(processName)s] %(module)s:%(lineno)d %(levelname)s - %(message)s",
        description="Format for TaskIQ worker logs"
    )
    log_date_format: str = Field(
        default="%Y-%m-%d %H:%M:%S",
        description="Date format for logs"
    )
    log_file: str = Field(
        default=str(BASE_DIR / "logs" / "app.log"),
        description="Path to log file"
    )
    log_file_max_size: int = Field(
        default=5 * 1024 * 1024,
        description="Maximum log file size in bytes (default: 5MB)"
    )
    log_file_backup_count: int = Field(
        default=3,
        description="Number of backup log files to keep"
    )

    @property
    def log_level_value(self) -> int:
        return logging.getLevelNamesMapping()[self.log_level.upper()]
