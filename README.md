# NutriCoreIQ

[![CI](https://github.com/dit99871/nutricoreiq_prod/actions/workflows/ci.yml/badge.svg)](https://github.com/dit99871/nutricoreiq_prod/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/dit99871/nutricoreiq_prod/branch/main/graph/badge.svg)](https://codecov.io/gh/dit99871/nutricoreiq_prod)
[![Python](https://img.shields.io/badge/python-3.13-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688.svg)](https://fastapi.tiangolo.com)

## Описание

NutriCoreIQ — это современное веб-приложение для расчёта нутриентов и калорий на основе физических параметров и целей пользователя. Приложение помогает пользователям составлять персонализированные планы питания для поддержания веса, набора массы или снижения веса.

[Официальный сайт](https://nutricoreiq.ru)

## Основные возможности

- **Расчёт TDEE** (Total Daily Energy Expenditure) на основе физических параметров
- **Расчёт BMR** (Basal Metabolic Rate) по формуле Mifflin-St Jeor
- **Персонализированные планы питания** с расчётом БЖУ (белки, жиры, углеводы)
- **Коррекция калорийности** в зависимости от цели (поддержание/набор/снижение веса)
- **Профиль пользователя** с детальной аналитикой и TDEE
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
- **Redis 8** — управление сессиями и кэширование
- **RabbitMQ 4** — очередь сообщений для асинхронных задач
- **Taskiq 0.11.18** — выполнение асинхронных задач

### Безопасность и аутентификация

- **JWT** с RSA ключами для аутентификации
- **CSRF защита** с токенами в cookie (double submit cookie pattern)
- **CSP (Content Security Policy)** с динамическим nonce
- **bcrypt** — хеширование паролей
- **Rate limiting** — защита от bruteforce атак через SlowAPI + Redis

### Фронтенд и шаблоны

- **Jinja2** — рендеринг HTML шаблонов
- **Bootstrap 5** — CSS фреймворк для адаптивного дизайна
- **JavaScript** — интерактивность на клиенте

### Мониторинг и логирование

- **Prometheus** — сбор метрик на `/metrics`
- **Grafana 11.6.11** — визуализация метрик
- **Sentry** — отслеживание ошибок в production
- **Loki 3.6.7** — агрегация логов
- **Alloy 1.4.0** — сбор логов и отправка в Loki
- **Node Exporter** — метрики системы
- **PostgreSQL/Redis/Nginx Exporters** — метрики баз данных и веб-сервера

### Деплой и инфраструктура

- **Docker** — контейнеризация приложения
- **Nginx** — reverse proxy и статические файлы
- **Gunicorn** — WSGI сервер для production
- **Uvicorn** — ASGI сервер
- **Alembic** — миграции базы данных

### Разработка и тестирование

- **uv** — управление зависимостями и виртуальным окружением
- **pytest + pytest-asyncio** — тестирование (16 модулей тестов)
- **pytest-cov** — покрытие кода
- **black, ruff, mypy, pylint** — линтеры и форматтеры
- **pre-commit hooks** — контроль качества кода

## Установка

1. Клонируйте репозиторий:
   ```bash
   git clone https://github.com/dit99871/nutricoreiq_prod.git
   cd nutricoreiq_prod
   ```

2. Установите uv, если ещё не установлен:
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

3. Установите зависимости:
   ```bash
   # только production-зависимости
   uv sync

   # с dev-зависимостями (для разработки)
   uv sync --group dev
   ```

4. Настройте файл окружения:
   ```bash
   cp .env.example .env
   ```
   Укажите в `.env` необходимые переменные (настройки базы данных, Redis, и т.д.).

5. Сгенерируйте пару ключей RSA для подписи JWT:
   ```bash
   mkdir -p src/app/core/certs
   openssl genrsa -out src/app/core/certs/jwt-private.pem 2048
   openssl rsa -in src/app/core/certs/jwt-private.pem -outform PEM -pubout -out src/app/core/certs/jwt-public.pem
   ```

6. Примените миграции базы данных:
   ```bash
   uv run alembic upgrade head
   ```

7. Запустите приложение:
   ```bash
   uv run uvicorn src.app.main:app --host 0.0.0.0 --port 8080
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
   uv run uvicorn src.app.main:app --reload
   ```

- **Запуск в production с Gunicorn**:
   ```bash
   uv run gunicorn -w 4 -k uvicorn.workers.UvicornWorker src.app.main:app
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

- `GET /user/profile/data` — страница профиля пользователя
- `POST /user/profile/update` — обновление профиля
- `GET /user/me` — базовая информация о пользователе

#### Продукты и нутриенты

- `GET /product` — информация о продуктах
- `POST /product` — добавление нового продукта
- `GET /product/{id}` — детальная информация о продукте

#### Безопасность и конфиденциальность

- `POST /privacy/consent` — управление согласием на обработку данных
- `GET /privacy/consent/status` — статус согласия
- `GET /security/csp-report` — репорт нарушений CSP

#### Информация и статус

- `GET /` - главная страница
- `GET /privacy` - информация о политике конфиденциальности
- `GET /about` - информация о проекте
- `GET /metrics` - Prometheus метрики
- `HEAD /` - для мониторинга (Sentry и пр.)

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
│   │   │   ├── auth.py        # JWT аутентификация
│   │   │   ├── cache.py       # Настройки кэширования
│   │   │   ├── cors.py        # CORS настройки
│   │   │   ├── db.py          # База данных
│   │   │   ├── env.py         # Окружение
│   │   │   ├── logging.py     # Логирование
│   │   │   ├── loki.py        # Loki настройки
│   │   │   ├── rate_limit.py  # Rate limiting
│   │   │   ├── redis.py       # Redis настройки
│   │   │   ├── routers_prefixs.py  # Префиксы роутеров
│   │   │   ├── run.py         # Настройки запуска
│   │   │   ├── sentry.py      # Sentry настройки
│   │   │   ├── settings.py    # Главный Settings
│   │   │   ├── smtp.py        # SMTP настройки
│   │   │   └── taskiq.py      # Taskiq настройки
│   │   ├── domain/            # Доменная логика
│   │   │   └── health/        # Расчёты здоровья
│   │   │       └── health_calculator.py
│   │   ├── middleware/        # Middleware стек (6 слоёв)
│   │   │   ├── base_middleware.py
│   │   │   ├── csp_middleware.py          # Content Security Policy
│   │   │   ├── csrf_protection_middleware.py  # CSRF защита
│   │   │   ├── http_middleware.py         # Логирование и трейсинг
│   │   │   ├── privacy_consent_middleware.py  # GDPR проверка
│   │   │   └── session_middleware.py      # Управление сессиями Redis
│   │   ├── models/            # SQLAlchemy модели базы данных
│   │   │   ├── base.py        # Базовая модель
│   │   │   ├── deleted_user.py  # Модель удалённых пользователей
│   │   │   ├── mixins/        # Миксины для моделей
│   │   │   ├── nutrient.py    # Модель нутриентов
│   │   │   ├── pending_product.py  # Модель ожидающих продуктов
│   │   │   ├── privacy_consent.py  # Модель согласий
│   │   │   ├── product.py     # Модель продуктов
│   │   │   ├── product_group.py  # Модель групп продуктов
│   │   │   ├── product_nutrient.py  # Связь продуктов и нутриентов
│   │   │   └── user.py        # Модель пользователя
│   │   ├── repo/              # Репозитории (работа с БД)
│   │   │   ├── pending_product.py  # Репозиторий ожидающих продуктов
│   │   │   ├── privacy_consent.py  # Репозиторий согласий
│   │   │   ├── product.py     # Репозиторий продуктов
│   │   │   ├── profile.py     # Репозиторий профилей
│   │   │   └── user.py        # Репозиторий пользователей
│   │   ├── schemas/           # Pydantic схемы для валидации
│   │   │   ├── base.py        # Базовые схемы
│   │   │   ├── privacy.py     # Схемы согласий
│   │   │   ├── product.py     # Схемы продуктов
│   │   │   ├── responses.py   # Схемы ответов
│   │   │   ├── security.py    # Схемы безопасности
│   │   │   └── user.py        # Схемы пользователей
│   │   ├── services/          # Бизнес-логика приложения
│   │   │   ├── cache.py               # Кэширование
│   │   │   ├── csp_service.py         # CSP сервис
│   │   │   ├── dummy_broker.py        # Тестовый брокер
│   │   │   ├── email.py               # Email уведомления
│   │   │   ├── jwt_service.py         # JWT сервис
│   │   │   ├── limiter.py             # Rate limiting
│   │   │   ├── log_context_service.py # Контекст логов
│   │   │   ├── privacy_service.py     # GDPR сервис
│   │   │   ├── product_service.py     # Сервис продуктов
│   │   │   ├── redis.py               # Redis операции
│   │   │   ├── sentry.py              # Sentry сервис
│   │   │   ├── session_service.py     # Сессии
│   │   │   ├── taskiq_broker.py       # Брокер задач
│   │   │   └── user_service.py        # Сервис пользователей
│   │   ├── tasks/             # Асинхронные задачи (Taskiq)
│   │   │   ├── sentry_task.py         # Отправка событий в Loki
│   │   │   └── welcome_email_notification.py
│   │   ├── utils/             # Вспомогательные утилиты
│   │   │   ├── auth.py        # Утилиты аутентификации
│   │   │   ├── case_converter.py  # Конвертер кейсов
│   │   │   ├── network.py     # Сетевые утилиты
│   │   │   ├── security.py    # Утилиты безопасности
│   │   │   ├── templates.py   # Утилиты шаблонов
│   │   │   ├── user.py        # Утилиты пользователей
│   │   │   └── validators.py  # Валидаторы
│   │   ├── app.py             # Конфигурация приложения
│   │   ├── constants.py       # Константы
│   │   ├── db_helper.py       # Помощник базы данных
│   │   ├── dependencies.py    # Зависимости FastAPI
│   │   ├── exception_handlers.py  # Обработчики исключений
│   │   ├── exceptions.py      # Кастомные исключения
│   │   ├── logger.py          # Логгер
│   │   └── redis.py           # Redis клиент
│   ├── alembic/               # Миграции базы данных
│   │   ├── versions/         # Версии миграций
│   │   ├── env.py            # Окружение Alembic
│   │   └── script.py.mako    # Шаблон миграций
│   ├── logs/                  # Логи приложения
│   ├── routers/               # API роутеры
│   │   ├── auth.py            # Аутентификация
│   │   ├── user.py            # Пользователи и профиль
│   │   ├── product.py         # Продукты и нутриенты
│   │   ├── privacy.py         # GDPR и согласие
│   │   ├── security.py        # CSP репорт
│   │   └── info.py            # Главная, о проекте, политика
│   ├── docker-compose.dev.yml # Development Docker Compose
│   ├── main.py                # Точка входа приложения
│   └── lifespan.py            # Lifespan события
├── tests/                     # Тесты
│   ├── unit/                  # Юнит-тесты
│   │   ├── test_domain/       # Тесты доменной логики
│   │   ├── test_exception_handlers.py
│   │   ├── test_middleware/   # Тесты middleware
│   │   ├── test_middleware_services.py
│   │   ├── test_repo/         # Тесты репозиториев
│   │   ├── test_routers/      # Тесты роутеров
│   │   ├── test_schemas/      # Тесты схем
│   │   ├── test_services/     # Тесты сервисов
│   │   └── test_utils/        # Тесты утилит
│   ├── integration/           # Интеграционные тесты
│   │   └── test_middleware_integration.py
│   └── conftest.py            # Конфигурация pytest
├── config/                    # Конфигурационные файлы
│   ├── fail2ban/              # Настройки Fail2ban
│   ├── logrotate.d/           # Настройки логов
│   ├── nginx/                 # Настройки Nginx
│   ├── prometheus.yml         # Конфигурация Prometheus
│   ├── loki-config.yaml       # Конфигурация Loki
│   └── alloy-config.alloy     # Конфигурация Alloy
├── scripts/                   # Скрипты
│   ├── deploy.sh              # Скрипт деплоя
│   └── entrypoint.sh          # Entrypoint для Docker
├── .github/                   # GitHub workflows
│   └── workflows/
│       └── ci.yml             # CI/CD пайплайн
├── docker-compose.prod.yml    # Production Docker Compose
├── Dockerfile                 # Основной Dockerfile
├── Dockerfile.nginx           # Nginx Dockerfile
├── pyproject.toml             # Зависимости и конфигурация проекта
├── uv.lock                    # Зафиксированные версии зависимостей
├── alembic.ini                # Конфигурация Alembic
├── .gitlab-ci.yml             # GitLab CI/CD конфигурация
├── .pre-commit-config.yaml   # Pre-commit hooks
├── .env.example               # Пример переменных окружения
└── README.md                  # Документация
```

### Архитектура приложения

**Многослойная архитектура:**

1. **Models** → SQLAlchemy модели базы данных
2. **Repo** → Репозитории для работы с БД
3. **Services** → Бизнес-логика и расчёты
4. **Routers** → HTTP обработчики и API

**Middleware стек (outer → inner):**

1. `HTTPMiddleware` — логирование, unified tracing, заголовки ответа
2. `SentryAsgiMiddleware` — отслеживание ошибок (только production)
3. `CORSMiddleware` — обработка CORS и preflight запросов
4. `SessionMiddleware` — управление сессиями Redis
5. `PrivacyConsentMiddleware` — проверка GDPR согласия
6. `CSRFProtectionMiddleware` — CSRF защита (double submit cookie)
7. `CSPMiddleware` — Content Security Policy с nonce

## Формулы расчётов

### BMR (Basal Metabolic Rate)

Формула Mifflin-St Jeor:
- **Для мужчин**: BMR = 10 × вес(кг) + 6.25 × рост(см) − 5 × возраст(лет) + 5
- **Для женщин**: BMR = 10 × вес(кг) + 6.25 × рост(см) − 5 × возраст(лет) − 161

### TDEE (Total Daily Energy Expenditure)

TDEE = BMR × KFA (коэффициент физической активности)

**Коэффициенты активности (KFA):**

| Уровень | Коэффициент | Описание |
|---------|-------------|----------|
| VERY_LOW | 1.2 | Очень низкий |
| LOW | 1.375 | Низкий |
| MEDIUM | 1.55 | Средний |
| HIGH | 1.725 | Высокий |
| VERY_HIGH | 1.9 | Очень высокий |

### Скорректированный TDEE

В зависимости от цели пользователя:
- **Поддержание веса**: TDEE без изменений
- **Набор веса**: TDEE + 400 ккал
- **Снижение веса**: TDEE − 500 ккал

### Расчёт нутриентов

Распределение БЖУ в зависимости от цели:

| Цель | Углеводы | Белки | Жиры |
|------|----------|-------|------|
| Поддержание веса | 55% | 20% | 25% |
| Набор веса | 55% | 25% | 20% |
| Снижение веса | 45% | 30% | 25% |

Перевод в граммы: углеводы и белки — 4 ккал/г, жиры — 9 ккал/г.

## Тестирование

```bash
# Все тесты
uv run pytest

# С покрытием кода
uv run pytest --cov=src --cov-report=html

# Только юнит-тесты
uv run pytest tests/unit/

# Интеграционные тесты
uv run pytest tests/integration/

# Тесты с маркерами
uv run pytest -m "not slow"   # пропустить медленные тесты
uv run pytest -m "not e2e"   # пропустить e2e тесты
```

### Категории тестов

- **unit** — юнит-тесты для отдельных компонентов (13 модулей)
- **integration** — тесты интеграции между компонентами
- **api** — тесты API эндпоинтов
- **db** — тесты, требующие доступа к базе данных
- **slow** — медленные тесты
- **asyncio** — асинхронные тесты
- **e2e** — end-to-end тесты, требующие запущенных сервисов

## Мониторинг и логирование

### Метрики

- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000
- **Node Exporter**: http://localhost:9100/metrics
- **PostgreSQL Exporter**: http://localhost:9187/metrics
- **Redis Exporter**: http://localhost:9121/metrics

### Логи

- **Loki**: http://localhost:3100
- **Alloy**: http://localhost:12345 (сбор логов и отправка)
- **Приложение**: `/src/app/logs/`

### Health Checks

- **База данных**: проверяется через Alembic connection
- **Redis**: проверяется через ping
- **RabbitMQ**: проверяется через diagnostics
- **Все сервисы**: health checks в docker-compose

## Производительность и безопасность

### Rate Limiting

- Регистрация: 5 запросов в минуту
- Вход: 5 запросов в минуту
- Смена пароля: 3 запроса в минуту
- Реализован через SlowAPI с Redis-хранилищем

### Безопасность

- **CSP** с динамическим nonce для inline скриптов
- **CSRF** токены в cookie с double submit cookie pattern
- **JWT** с RSA256 подписью, ключи в `src/app/core/certs/`
- **bcrypt** для хеширования паролей
- **HTTPS** в production с Let's Encrypt
- **Trusted proxies** для корректного определения IP
- **Rate limiting** через SlowAPI
- **Privacy consent** проверка GDPR

## Лицензия

MIT License

## Контакты

- Email: [dit99871@gmail.com](mailto:dit99871@gmail.com)
- Telegram: [di_99871](https://t.me/di_99871)

## Статус проекта

**Версия**: 0.1.0
**Статус**: Активно поддерживается
**Python**: 3.13+
**FastAPI**: 0.115.11

Проект активно поддерживается и развивается с соблюдением современных практик разработки и production-ready инфраструктурой.