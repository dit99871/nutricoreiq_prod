NutriCoreIQ
Описание
NutriCoreIQ — это веб-приложение, которое помогает пользователям анализировать ценность продуктов питания, предоставляя информацию о питательных веществах и их влиянии на здоровье. Проект направлен на упрощение принятия осознанных решений о питании.
Технологии

Python 3.13
FastAPI — для создания API
SQLAlchemy и asyncpg — для работы с базой данных
Redis — для кэширования и сессий
Jinja2 — для шаблонов
Prometheus — для мониторинга
Uvicorn и Gunicorn — для запуска сервера
Alembic — для миграций базы данных
Pydantic — для валидации данных
Taskiq — для асинхронных задач
Poetry — для управления зависимостями
Тестирование: pytest, pytest-asyncio, pytest-cov
Линтеры и форматтеры: black, ruff, mypy, pylint
Прочее: python-jose, bcrypt, httpx, aiosmtplib

Установка

Клонируйте репозиторий:git clone https://github.com/username/NutriCoreIQ.git


Установите Poetry, если еще не установлен:pip install poetry


Установите зависимости:poetry install


Настройте окружение:cp .env.example .env

Укажите в .env необходимые переменные (например, настройки базы данных, Redis, ключи JWT).
Сгенерируйте пару ключей RSA для подписи JWT:# Generate an RSA private key, of size 2048
openssl genrsa -out src/app/core/certs/jwt-private.pem 2048

# Extract the public key from the key pair
openssl rsa -in src/app/core/certs/jwt-private.pem -outform PEM -pubout -out src/app/core/certs/jwt-public.pem


Примените миграции базы данных:poetry run alembic upgrade head


Запустите приложение:poetry run uvicorn src.app.main:app --host 0.0.0.0 --port 8000



Использование

Запуск сервера:poetry run uvicorn src.app.main:app --reload

Для продакшена используйте Gunicorn:poetry run gunicorn -w 4 -k uvicorn.workers.UvicornWorker src.app.main:app


Доступ к API: Откройте http://localhost:8000/docs для интерактивной документации Swagger.
Основные эндпоинты:
/auth/register — регистрация нового пользователя
/product — информация о продуктах и их питательной ценности
/user — управление профилем пользователя


Пример запроса: Регистрация нового пользователя:curl -X POST "http://localhost:8000/auth/register" \
-H "Content-Type: application/json" \
-d '{"username": "john_doe", "email": "john@example.com", "password": "securepassword123"}'

Ожидаемый ответ:{
    "username": "john_doe",
    "email": "john@example.com",
    "is_subscribed": true
}



Структура репозитория

src/app/ — Основной код приложения
core/ — Конфигурации, логика сервисов, middleware (CSP, CSRF, Redis)
crud/ — Операции с базой данных (пользователи, профили)
models/ — Модели базы данных (продукты, питательные вещества, пользователи)
routers/ — Маршруты API (аутентификация, поиск продуктов, пользователи)
schemas/ — Схемы Pydantic для валидации
static/ — Статические файлы (CSS, JS, изображения)
templates/ — HTML-шаблоны (Jinja2)
tasks/ — Асинхронные задачи (например, отправка приветственных писем)


alembic/ — Миграции базы данных
docker-compose.prod.yml — Конфигурация для продакшена
Dockerfile, Dockerfile.nginx — Контейнеры для приложения и Nginx

Лицензия
MIT License
Контакты

Email: dit99871@gmail.com
Telegram: di_99871

Статус проекта
Проект активно поддерживается.