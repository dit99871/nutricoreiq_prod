# NutriCoreIQ

## Описание
NutriCoreIQ — это современное веб-приложение для расчета нутриентов и калорий на основе физических параметров и целей пользователя. Приложение помогает пользователям составлять персонализированные планы питания для поддержания веса, набора массы или снижения веса.

[Официальный сайт](https://nutricoreiq.ru)

## Основные возможности
- **Расчет TDEE** (Total Daily Energy Expenditure) на основе физических параметров
- **Персонализированные планы питания** с расчетом БЖУ (белки, жиры, углеводы)
- **Коррекция калорийности** в зависимости от цели (поддержание/набор/снижение веса)
- **Профиль пользователя** с детальной аналитикой
- **Аутентификация и авторизация** с JWT токенами
- **GDPR compliance** с управлением согласием на обработку данных
- **CSRF защита** и современные меры безопасности
- **Мониторинг** с Prometheus, Grafana и Sentry

## Технологии

### Backend
- **Python 3.13+** — основной язык разработки
- **FastAPI 0.115.11** — современный фреймворк для создания API
- **SQLAlchemy 2.0+** с asyncpg — ORM и асинхронный драйвер для PostgreSQL
- **PostgreSQL 17** — основная база данных
- **Redis 6.2.0** — управление сессиями и кэширование
- **RabbitMQ** — очередь сообщений для асинхронных задач
- **Taskiq** — выполнение асинхронных задач

### Безопасность и аутентификация
- **JWT** с RSA ключами для аутентификации
- **CSRF защита** с токенами в cookie
- **CSP (Content Security Policy)** с динамическим nonce
- **bcrypt** — хеширование паролей
- **Rate limiting** — защита от bruteforce атак

### Фронтенд и шаблоны
- **Jinja2** — рендеринг HTML шаблонов
- **Bootstrap 5** — CSS фреймворк для адаптивного дизайна
- **JavaScript** — интерактивность на клиенте

### Мониторинг и логирование
- **Prometheus** — сбор метрик на `/metrics`
- **Grafana** — визуализация метрик
- **Sentry** — отслеживание ошибок в production
- **Loki + Promtail** — агрегация логов
- **Node Exporter** — метрики системы
- **PostgreSQL/Redis Exporters** — метрики баз данных

### Деплой и инфраструктура
- **Docker** — контейнеризация приложения
- **Nginx** — reverse proxy и статические файлы
- **Gunicorn** — WSGI сервер для production
- **Uvicorn** — ASGI сервер
- **Alembic** — миграции базы данных

### Разработка и тестирование
- **Poetry** — управление зависимостями
- **pytest + pytest-asyncio** — тестирование
- **pytest-cov** — покрытие кода
- **black, ruff, mypy, pylint** — линтеры и форматтеры
- **pre-commit hooks** — контроль качества кода

## Установка

1. Клонируйте репозиторий:
   ```bash
   git clone https://github.com/dit99871/nutricoreiq_prod.git
   ```

2. Установите Poetry, если он еще не установлен:
   ```bash
   pip install poetry
   ```

3. Установите зависимости:
   ```bash
   poetry install
   ```

4. Настройте файл окружения:
   ```bash
   cp .env.example .env
   ```
   Укажите в `.env` необходимые переменные (например, настройки базы данных, Redis, ключи JWT).

5. Сгенерируйте пару ключей RSA для подписи JWT:
   ```bash
   mkdir -p src/app/core/certs
   openssl genrsa -out src/app/core/certs/jwt-private.pem 2048
   openssl rsa -in src/app/core/certs/jwt-private.pem -outform PEM -pubout -out src/app/core/certs/jwt-public.pem
   ```

6. Примените миграции базы данных:
   ```bash
   poetry run alembic upgrade head
   ```

7. Запустите приложение:
   ```bash
   poetry run uvicorn src.app.main:app --host 0.0.0.0 --port 8080
   ```

### Docker запуск

Для разработки с Docker Compose:
```bash
docker-compose -f docker-compose.dev.yml up -d
```

Для production:
```bash
docker-compose -f docker-compose.prod.yml up -d
```

## Использование

- **Запуск сервера в режиме разработки**:
   ```bash
   poetry run uvicorn src.app.main:app --reload
   ```

- **Запуск в продакшене с Gunicorn**:
   ```bash
   poetry run gunicorn -w 4 -k uvicorn.workers.UvicornWorker src.app.main:app
   ```

- **Доступ к API**: Откройте [Swagger документацию](http://localhost:8080/docs) для интерактивной документации API.

### Основные эндпоинты
#### Аутентификация
- `POST /auth/register` — регистрация нового пользователя
- `POST /auth/login` — вход пользователя
- `POST /auth/logout` — выход пользователя
- `POST /auth/refresh` — обновление токена
- `GET /auth/me` — информация о текущем пользователе

#### Профиль и аналитика
- `GET /user/profile` — страница профиля пользователя
- `GET /profile/data` — данные профиля для AJAX
- `GET /user/profile/data` — API эндпоинт профиля
- `PUT /user/profile` — обновление профиля

#### Продукты и нутриенты
- `GET /product` — информация о продуктах
- `POST /product` — добавление нового продукта
- `GET /product/{id}` — детальная информация о продукте

#### Безопасность и конфиденциальность
- `POST /privacy/consent` — управление согласием на обработку данных
- `GET /privacy/policy` — политика конфиденциальности
- `GET /security/csrf-token` — получение CSRF токена

#### Информация и статус
- `GET /info/health` — проверка здоровья приложения
- `GET /info/version` — версия приложения
- `GET /metrics` — Prometheus метрики

### Пример запроса
Регистрация нового пользователя:
```bash
curl -X POST "http://localhost:8080/auth/register" \
-H "Content-Type: application/json" \
-d '{"username": "john_doe", "email": "john@example.com", "password": "securepassword123"}'
```

Ожидаемый ответ:
```json
{
    "username": "john_doe",
    "email": "john@example.com",
    "is_subscribed": true
}
```

## Структура репозитория

```
nutricoreiq_prod/
├── src/app/                    # Основной код приложения
│   ├── core/                   # Ядро приложения
│   │   ├── config/            # Конфигурации (Pydantic Settings)
│   │   ├── domain/            # Доменные модели
│   │   ├── middleware/        # Промежуточное ПО (CSP, CSRF, Redis)
│   │   │   ├── csp.py         # Content Security Policy
│   │   │   ├── csrf.py        # CSRF защита
│   │   │   ├── session.py     # Управление сессиями Redis
│   │   │   ├── privacy.py     # GDPR согласие
│   │   │   └── security.py    # Безопасность
│   │   ├── models/            # SQLAlchemy модели базы данных
│   │   │   ├── user.py        # Модель пользователя
│   │   │   ├── product.py     # Модель продуктов
│   │   │   └── nutrients.py   # Модель нутриентов
│   │   ├── repo/              # Репозитории (работа с БД)
│   │   ├── schemas/           # Pydantic схемы для валидации
│   │   ├── services/          # Бизнес-логика приложения
│   │   │   ├── user.py        # Сервис пользователей
│   │   │   ├── health.py      # Расчеты TDEE и нутриентов
│   │   │   └── auth.py        # Сервис аутентификации
│   │   ├── tasks/             # Асинхронные задачи (Taskiq)
│   │   ├── utils/             # Вспомогательные утилиты
│   │   └── certs/             # RSA ключи для JWT
│   ├── routers/               # API роутеры
│   │   ├── auth.py            # Аутентификация
│   │   ├── user.py            # Пользователи и профиль
│   │   ├── product.py         # Продукты и нутриенты
│   │   ├── privacy.py         # GDPR и согласие
│   │   ├── security.py        # Безопасность
│   │   └── info.py            # Информация о системе
│   ├── static/                # Статические файлы (CSS, JS, изображения)
│   │   ├── css/               # Стили
│   │   ├── js/                # JavaScript файлы
│   │   └── images/            # Изображения
│   ├── templates/             # HTML-шаблоны (Jinja2)
│   │   ├── auth/              # Шаблоны аутентификации
│   │   ├── user/              # Шаблоны профиля
│   │   └── components/        # Переиспользуемые компоненты
│   ├── main.py                # Точка входа приложения
│   └── lifespan.py            # Lifespan события
├── tests/                     # Тесты
│   ├── unit/                  # Юнит-тесты
│   │   ├── test_health.py     # Тесты расчетов
│   │   ├── test_user.py       # Тесты пользователей
│   │   └── test_auth.py       # Тесты аутентификации
│   ├── integration/           # Интеграционные тесты
│   └── conftest.py            # Конфигурация pytest
├── alembic/                   # Миграции базы данных
├── config/                    # Конфигурационные файлы
│   ├── prometheus.yml         # Конфигурация Prometheus
│   ├── loki-config.yaml       # Конфигурация Loki
│   └── promtail-config.yaml   # Конфигурация Promtail
├── scripts/                   # Скрипты деплоя
├── docker-compose.prod.yml    # Production Docker Compose
├── docker-compose.dev.yml     # Development Docker Compose
├── Dockerfile                 # Основной Dockerfile
├── Dockerfile.nginx           # Nginx Dockerfile
├── pyproject.toml             # Poetry зависимости
└── alembic.ini                # Конфигурация Alembic
```

### Архитектура приложения

**Многослойная архитектура:**
1. **Models** → SQLAlchemy модели базы данных
2. **Repo** → Репозитории для работы с БД
3. **Services** → Бизнес-логика и расчеты
4. **Routers** → HTTP обработчики и API

**Middleware стек (inner → outer):**
1. CSPSecurityMiddleware — Content Security Policy
2. CSRFProtectionMiddleware — CSRF защита
3. RedisSessionMiddleware — Управление сессиями
4. PrivacyConsentMiddleware — GDPR согласие
5. SentryAsgiMiddleware — Отслеживание ошибок (production)
6. CORSMiddleware — Cross-origin запросы
7. HTTPEnhancedMiddleware — Логирование и обработка ошибок

## Тестирование

### Запуск тестов
```bash
# Все тесты
poetry run pytest

# С покрытием кода
poetry run pytest --cov=src --cov-report=html

# Только юнит-тесты
poetry run pytest tests/unit/

# Интеграционные тесты
poetry run pytest tests/integration/

# Тесты с маркерами
poetry run pytest -m "not slow"  # пропустить медленные тесты
poetry run pytest -m "api"       # только API тесты
```

### Категории тестов
- **unit** — юнит-тесты для отдельных компонентов
- **integration** — тесты интеграции между компонентами
- **api** — тесты API эндпоинтов
- **db** — тесты требующие доступа к базе данных
- **slow** — медленные тесты
- **asyncio** — асинхронные тесты

## Мониторинг и логирование

### Метрики
- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000
- **Node Exporter**: http://localhost:9100/metrics
- **PostgreSQL Exporter**: http://localhost:9187/metrics
- **Redis Exporter**: http://localhost:9121/metrics

### Логи
- **Loki**: http://localhost:3100
- **Приложение**: `/src/app/logs/`
- **Nginx**: `/logs/nginx/`

### Health Checks
- **Приложение**: http://localhost:8080/info/health
- **База данных**: проверяется через Alembic connection
- **Redis**: проверяется через ping
- **RabbitMQ**: проверяется через diagnostics

## Производительность и безопасность

### Rate Limiting
- Регистрация: 5 запросов в минуту
- Вход: 5 запросов в минуту
- Смена пароля: 3 запроса в минуту

### Безопасность
- **CSP** с динамическим nonce для inline скриптов
- **CSRF** токены в cookie с double submit cookie pattern
- **JWT** с RSA256 подписью
- **bcrypt** для хеширования паролей
- **HTTPS** в production с Let's Encrypt
- **Trusted proxies** для корректного определения IP

## Лицензия
MIT License

## Контакты
- Email: [dit99871@gmail.com](mailto:dit99871@gmail.com)
- Telegram: [di_99871](https://t.me/di_99871)

## Статус проекта
Проект активно поддерживается.