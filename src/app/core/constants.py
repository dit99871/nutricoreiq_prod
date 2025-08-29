from __future__ import annotations
from pathlib import Path
from fastapi import HTTPException
from fastapi import status

# Base directory of the project (src/app/)
BASE_DIR = Path(__file__).resolve().parent.parent

# User profile constants
MIN_AGE: int = 10

# JWT constants
TOKEN_TYPE_FIELD = "type"
ACCESS_TOKEN_TYPE = "access"
REFRESH_TOKEN_TYPE = "refresh"

# Authentication constants
CREDENTIAL_EXCEPTION = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail={"message": "Oшибка аутентификации. Пожалуйста, войдите заново"},
    headers={"WWW-Authenticate": "Bearer"},
)
