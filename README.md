# NutricoreIQ

NutricoreIQ - это API сервис для работы с информацией о продуктах питания и их пищевой ценности.

## Технологии

- Python 3.13+
- FastAPI
- SQLAlchemy (с поддержкой asyncio)
- PostgreSQL (asyncpg)
- Redis
- Poetry для управления зависимостями
- Alembic для миграций базы данных

## Установка

1. Клонируйте репозиторий:
```bash
git clone https://github.com/yourusername/nutricoreiq.git
cd nutricoreiq
```

2. Установите Poetry (если еще не установлен):
```bash
curl -sSL https://install.python-poetry.org | python3 -
```

3. Установите зависимости:
```bash
poetry install
```

4. Создайте файл .env в корневой директории проекта и настройте переменные окружения.

5. Примените миграции базы данных:
```bash
poetry run alembic upgrade head
```

## Запуск

Для запуска сервера разработки:
```bash
poetry run uvicorn src.app.main:app --reload
```

API будет доступен по адресу: http://localhost:8000

Документация API: http://localhost:8000/docs

## Тестирование

Для запуска тестов:
```bash
poetry run pytest
```

## Лицензия

MIT