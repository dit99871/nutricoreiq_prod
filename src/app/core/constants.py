from __future__ import annotations

from pathlib import Path

from src.app.core.exceptions import AuthenticationError

# константа базовой директории проекта (src/app/)
BASE_DIR = Path(__file__).resolve().parent.parent

# константы профилей
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

# константы аутентификации
CREDENTIAL_EXCEPTION = AuthenticationError(
    "Oшибка аутентификации. Пожалуйста, войдите заново"
)
