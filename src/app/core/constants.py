from __future__ import annotations

from pathlib import Path

from fastapi import HTTPException, status

# Константа базовой директории проекта (src/app/)
BASE_DIR = Path(__file__).resolve().parent.parent

# Константы профилей
MIN_AGE: int = 10
MAX_AGE: int = 120

MIN_HEIGHT_CM: int = 50
MAX_HEIGHT_CM: int = 300

MIN_WEIGHT_KG: int = 20
MAX_WEIGHT_KG: int = 400

# JWT константы
TOKEN_TYPE_FIELD = "type"
ACCESS_TOKEN_TYPE = "access_token"
REFRESH_TOKEN_TYPE = "refresh_token"

# Константы аутентификации
CREDENTIAL_EXCEPTION = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail={"message": "Oшибка аутентификации. Пожалуйста, войдите заново"},
    headers={"WWW-Authenticate": "Bearer"},
)

# Константы логирования
LOG_DEFAULT_FORMAT = (
    "[%(asctime)s.%(msecs)03d] %(name)s:%(lineno)d %(levelname)s - %(message)s"
)
WORKER_LOG_DEFAULT_FORMAT = (
    "[%(asctime)s.%(msecs)03d] [%(processName)s] %(module)s:%(lineno)d "
    "%(levelname)s - %(message)s"
)
