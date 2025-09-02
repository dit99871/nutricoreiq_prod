from fastapi.templating import Jinja2Templates

from src.app.core.constants import BASE_DIR

# Настройка шаблонов
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
