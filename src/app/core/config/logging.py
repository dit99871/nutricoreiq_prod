import logging
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

BASE_DIR = Path(__file__).resolve().parent.parent.parent
LOG_DEFAULT_FORMAT = (
    "[%(asctime)s.%(msecs)03d] %(name)24s:%(lineno)-4d %(levelname)-7s - %(message)s"
)
WORKER_LOG_DEFAULT_FORMAT = "[%(asctime)s.%(msecs)03d] [%(processName)s] %(module)16s:%(lineno)-3d %(levelname)-7s - %(message)s"


class LoggingConfig(BaseModel):
    log_level: Literal[
        "DEBUG",
        "INFO",
        "WARNING",
        "ERROR",
        "CRITICAL",
    ] = "INFO"
    log_stage: Literal["DEV", "PROD"] = "DEV"
    log_format: str = LOG_DEFAULT_FORMAT
    log_taskiq_format: str = WORKER_LOG_DEFAULT_FORMAT
    log_date_format: str = "%Y-%m-%d %H:%M:%S"
    log_file: str = str(BASE_DIR / "logs" / "app.log")  # Путь к файлу логов
    log_file_max_size: int = 5 * 1024 * 1024  # 5 MB
    log_file_backup_count: int = 3  # Количество backup файлов

    @property
    def log_level_value(self) -> int:
        return logging.getLevelNamesMapping()[self.log_level.upper()]
