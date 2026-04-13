"""Настройка Jinja2 шаблонов для FastAPI."""

from fastapi.templating import Jinja2Templates

from src.app.core.constants import BASE_DIR

templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
