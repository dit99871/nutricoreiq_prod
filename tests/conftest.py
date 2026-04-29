"""
Корневой conftest.py — выставляет переменные окружения ДО любых импортов,
чтобы pydantic-settings мог создать Settings() при коллекции тестов.
"""

import os
import sys
from pathlib import Path

# добавляем корень проекта в путь
project_root = Path(__file__).parent.resolve()
sys.path.insert(0, str(project_root))


def pytest_configure(config):
    """Выставляет переменные из env до импорта любых модулей приложения."""
    defaults = {
        # auth
        "APP_CONFIG__AUTH__ALGORITHM": "RS256",
        "APP_CONFIG__AUTH__ACCESS_TOKEN_EXPIRES": "15",
        "APP_CONFIG__AUTH__REFRESH_TOKEN_EXPIRES": "7",
        # cache
        "APP_CONFIG__CACHE__USER_TTL": "3600",
        "APP_CONFIG__CACHE__CONSENT_TTL": "3600",
        # CORS
        "APP_CONFIG__CORS__ALLOW_ORIGINS": '["http://localhost"]',
        "APP_CONFIG__CORS__ALLOW_METHODS": '["GET","POST","PUT","DELETE","PATCH","OPTIONS"]',
        "APP_CONFIG__CORS__ALLOW_HEADERS": '["*"]',
        "APP_CONFIG__CORS__ALLOW_CREDENTIALS": "true",
        # DB
        "APP_CONFIG__DB__URL": "postgresql+asyncpg://test:test@localhost:5432/testdb",
        "APP_CONFIG__DB__ECHO": "false",
        # env
        "APP_CONFIG__ENV__ENV": "test",
        # SMTP
        "APP_CONFIG__MAIL__HOST": "localhost",
        "APP_CONFIG__MAIL__PORT": "25",
        "APP_CONFIG__MAIL__BUTTON_LINK": "http://localhost/login",
        "APP_CONFIG__MAIL__UNSUBSCRIBE_LINK": "http://localhost/unsub",
        # Redis
        "APP_CONFIG__REDIS__URL": "redis://localhost:6379",
        "APP_CONFIG__REDIS__SALT": "test-salt-for-hashing",
        "APP_CONFIG__REDIS__PASSWORD": "testpassword",
        "APP_CONFIG__REDIS__SESSION_TTL": "3600",
        # Run
        "APP_CONFIG__RUN__HOST": "0.0.0.0",
        "APP_CONFIG__RUN__PORT": "8000",
        # Taskiq
        "APP_CONFIG__TASKIQ__URL": "amqp://guest:guest@localhost:5672/",
    }
    for key, value in defaults.items():
        os.environ.setdefault(key, value)