# NutriCoreIQ

## Описание
NutriCoreIQ — это современное веб-приложение для расчета нутриентов и калорий на основе физических параметров и целей пользователя. Приложение помогает пользователям составлять персонализированные планы питания для поддержания веса, набора массы или снижения веса.

[Официальный сайт](https://nutricoreiq.ru)

## Основные возможности
- **Расчет TDEE** (Total Daily Energy Expenditure) на основе физических параметров
- **Расчет BMR** (Basal Metabolic Rate) по формуле Mifflin-St Jeor
- **Персонализированные планы питания** с расчетом БЖУ (белки, жиры, углеводы)
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
- **Grafana 11.6.11** — визуализация метрик
- **Sentry** — отслеживание ошибок в production
- **Loki 3.6.7** — агрегация логов
- **Alloy 1.4.0** — сбор логов и метрик
- **Node Exporter** — метрики системы
- **PostgreSQL/Redis/Nginx Exporters** — метрики баз данных и веб-сервера

### Деплой и инфраструктура
- **Docker** — контейнеризация приложения
- **Nginx** — reverse proxy и статические файлы
- **Gunicorn** — WSGI сервер для production
- **Uvicorn** — ASGI сервер
- **Alembic** — миграции базы данных

### Разработка и тестирование
- **Poetry** — управление зависимостями
- **pytest + pytest-asyncio** — тестирование (16 тестовых файлов)
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
│   │   │   ├── auth.py        # JWT аутентификация
│   │   │   ├── cache.py       # Настройки кэширования
│   │   │   ├── cors.py        # CORS настройки
│   │   │   ├── db.py          # База данных
│   │   │   ├── env.py         # Переменные окружения
│   │   │   ├── logging.py     # Логирование
│   │   │   ├── loki.py        # Loki интеграция
│   │   │   ├── rate_limit.py # Rate limiting
│   │   │   ├── redis.py       # Redis настройки
│   │   │   ├── sentry.py      # Sentry интеграция
│   │   │   ├── settings.py    # Основные настройки
│   │   │   └── taskiq.py      # Taskiq брокер
│   │   ├── domain/            # Доменная логика
│   │   │   └── health/        # Расчеты здоровья
│   │   │       └── health_calculator.py
│   │   ├── middleware/        # Промежуточное ПО (7 middleware)
│   │   │   ├── base_middleware.py
│   │   │   ├── csp_middleware.py         # Content Security Policy
│   │   │   ├── csrf_protection_middleware.py # CSRF защита
│   │   │   ├── http_middleware.py        # Логирование и обработка ошибок
│   │   │   ├── privacy_consent_middleware.py # GDPR согласие
│   │   │   └── session_middleware.py     # Управление сессиями Redis
│   │   ├── models/            # SQLAlchemy модели базы данных
│   │   │   ├── user.py        # Модель пользователя
│   │   │   ├── product.py     # Модель продуктов
│   │   │   └── privacy_consent.py # Модель согласия
│   │   ├── repo/              # Репозитории (работа с БД)
│   │   ├── schemas/           # Pydantic схемы для валидации
│   │   ├── services/          # Бизнес-логика приложения (15 сервисов)
│   │   │   ├── user_service.py        # Сервис пользователей
│   │   │   ├── jwt_service.py         # JWT токены
│   │   │   ├── cache_service.py       # Кэширование
│   │   │   ├── email_service.py       # Email уведомления
│   │   │   ├── limiter.py             # Rate limiting
│   │   │   ├── log_context_service.py # Контекст логирования
│   │   │   ├── privacy_service.py     # GDPR сервис
│   │   │   ├── redis_service.py       # Redis операции
│   │   │   ├── session_service.py     # Сессии
│   │   │   └── taskiq_broker.py       # Асинхронные задачи
│   │   ├── tasks/             # Асинхронные задачи (Taskiq)
│   │   ├── utils/             # Вспомогательные утилиты
│   │   └── certs/             # RSA ключи для JWT
│   ├── routers/               # API роутеры (6 роутеров)
│   │   ├── auth.py            # Аутентификация
│   │   ├── user.py            # Пользователи и профиль
│   │   ├── product.py         # Продукты и нутриенты
│   │   ├── privacy.py         # GDPR и согласие
│   │   ├── security.py        # Безопасность
│   │   └── info.py            # Информация о системе
│   ├── static/                # Статические файлы (CSS, JS, изображения)
│   ├── templates/             # HTML-шаблоны (Jinja2)
│   │   ├── auth/              # Шаблоны аутентификации
│   │   ├── user/              # Шаблоны профиля
│   │   └── components/        # Переиспользуемые компоненты
│   ├── main.py                # Точка входа приложения
│   └── lifespan.py            # Lifespan события
├── tests/                     # Тесты (16 файлов)
│   ├── unit/                  # Юнит-тесты
│   │   ├── test_domain/       # Тесты доменной логики
│   │   ├── test_health.py     # Тесты расчетов TDEE и нутриентов
│   │   ├── test_user.py       # Тесты пользователей
│   │   ├── test_auth.py       # Тесты аутентификации
│   │   ├── test_middleware_services.py # Тесты middleware и сервисов
│   │   ├── test_repo/         # Тесты репозиториев
│   │   ├── test_schemas/      # Тесты схем
│   │   └── test_utils/        # Тесты утилит
│   ├── integration/           # Интеграционные тесты
│   │   └── test_middleware_integration.py
│   └── conftest.py            # Конфигурация pytest
├── alembic/                   # Миграции базы данных
├── config/                    # Конфигурационные файлы
│   ├── prometheus.yml         # Конфигурация Prometheus
│   ├── loki-config.yaml       # Конфигурация Loki
│   └── alloy-config.alloy     # Конфигурация Alloy
├── scripts/                   # Скрипты деплоя
│   ├── deploy.sh              # Скрипт деплоя
│   └── entrypoint.sh          # Entrypoint для Docker
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

## Расчеты и формулы

### BMR (Basal Metabolic Rate)
Расчет по формуле Mifflin-St Jeor:
- **Для мужчин**: BMR = 10 × вес(кг) + 6.25 × рост(см) - 5 × возраст(лет) + 5
- **Для женщин**: BMR = 10 × вес(кг) + 6.25 × рост(см) - 5 × возраст(лет) - 161

### TDEE (Total Daily Energy Expenditure)
TDEE = BMR × KFA (коэффициент физической активности)

**Коэффициенты активности (KFA):**
- VERY_LOW: 1.2 (минимальная активность)
- LOW: 1.375 (легкая активность)
- MEDIUM: 1.55 (умеренная активность)
- HIGH: 1.725 (высокая активность)
- VERY_HIGH: 1.9 (очень высокая активность)

### Скорректированный TDEE
В зависимости от цели пользователя:
- **Поддержание веса**: TDEE без изменений
- **Набор веса**: TDEE + 400 ккал
- **Снижение веса**: TDEE - 500 ккал

### Расчет нутриентов
Процентное соотношение БЖУ в зависимости от цели:
- **Поддержание веса**: 55% углеводы, 20% белки, 25% жиры
- **Набор веса**: 55% углеводы, 25% белки, 20% жиры
- **Снижение веса**: 45% углеводы, 30% белки, 25% жиры

Перевод в граммы:
- **Углеводы и белки**: калории ÷ 4 ккал/г
- **Жиры**: калории ÷ 9 ккал/г

**Middleware стек (inner → outer):**
1. CSPMiddleware — Content Security Policy с динамическим nonce
2. CSRFProtectionMiddleware — CSRF защита с double submit cookie pattern
3. SessionMiddleware — Управление сессиями в Redis
4. PrivacyConsentMiddleware — GDPR согласие на обработку данных
5. CORSMiddleware — Обработка CORS и preflight запросов
6. SentryAsgiMiddleware — Отслеживание ошибок (только в production)
7. HTTPMiddleware — Логирование, unified tracing и обработка ошибок

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
- **unit** — юнит-тесты для отдельных компонентов (13 файлов)
- **integration** — тесты интеграции между компонентами
- **api** — тесты API эндпоинтов
- **db** — тесты требующие доступа к базе данных
- **slow** — медленные тесты
- **asyncio** — асинхронные тесты
- **e2e** — end-to-end тесты requiring running services

## Мониторинг и логирование

### Метрики
- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000
- **Node Exporter**: http://localhost:9100/metrics
- **PostgreSQL Exporter**: http://localhost:9187/metrics
- **Redis Exporter**: http://localhost:9121/metrics

### Логи
- **Loki**: http://localhost:3100
- **Alloy**: http://localhost:12345 (сбор логов и метрик)
- **Приложение**: `/src/app/logs/`
- **Nginx**: `/logs/nginx/`

### Health Checks
- **Приложение**: http://localhost:8080/info/health
- **База данных**: проверяется через Alembic connection
- **Redis**: проверяется через ping
- **RabbitMQ**: проверяется через diagnostics
- **Все сервисы**: health checks в docker-compose

## Производительность и безопасность

### Rate Limiting
- Регистрация: 5 запросов в минуту
- Вход: 5 запросов в минуту
- Смена пароля: 3 запроса в минуту
- Реализовано через SlowAPI с Redis хранением

### Безопасность
- **CSP** с динамическим nonce для inline скриптов
- **CSRF** токены в cookie с double submit cookie pattern
- **JWT** с RSA256 подписью и ключами в `/src/app/core/certs/`
- **bcrypt** для хеширования паролей
- **HTTPS** в production с Let's Encrypt
- **Trusted proxies** для корректного определения IP
- **Rate limiting** через SlowAPI
- **Privacy consent** согласно GDPR

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

Проект находится в активной разработке с регулярными обновлениями и улучшениями архитектуры.