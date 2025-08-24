from __future__ import annotations
from pathlib import Path

# Base directory of the project (src/app/)
BASE_DIR = Path(__file__).resolve().parent.parent

# Диапазоны для профиля пользователя
MIN_AGE: int = 10
MAX_AGE: int = 120

MIN_HEIGHT_CM: int = 50
MAX_HEIGHT_CM: int = 300

MIN_WEIGHT_KG: int = 20
MAX_WEIGHT_KG: int = 400
