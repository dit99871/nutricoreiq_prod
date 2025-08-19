# Анализ производительности - NutriCoreIQ

## Общая оценка: 7/10

### ✅ Хорошие решения для производительности

#### 1. Асинхронная архитектура
```python
# Полностью асинхронный stack
- FastAPI (async/await)
- SQLAlchemy 2.0 (async)
- asyncpg (PostgreSQL async driver)
- aioredis (Redis async client)
- aiosmtplib (SMTP async)
```

#### 2. Кэширование
```python
# Redis для кэширования
- Сессии пользователей
- Refresh токены
- Потенциально результаты запросов

# Session middleware с Redis
class RedisSessionMiddleware:
    # TTL для автоматической очистки
    session_ttl: int
```

#### 3. Оптимизация БД запросов
```python
# Правильная настройка lazy loading
product_groups: Mapped["ProductGroup"] = relationship(
    back_populates="products",
    lazy="joined"  # Eager loading для часто используемых связей
)

nutrient_associations: Mapped[list["ProductNutrient"]] = relationship(
    back_populates="products",
    lazy="selectin"  # Эффективное loading для списков
)
```

#### 4. Индексы БД
```python
# PostgreSQL оптимизации
- GIN индекс для полнотекстового поиска
- Trigram индекс для нечеткого поиска
- Обычные B-tree индексы на ключевые поля

Index("idx_product_search_vector", search_vector, postgresql_using="gin")
Index("idx_product_title_trgm", title, postgresql_using="gin",
      postgresql_ops={"title": "gin_trgm_ops"})
```

#### 5. Connection pooling
```python
# SQLAlchemy connection pool
pool_size: int = 50
max_overflow: int = 10
echo_pool: bool = False  # Не логировать pool events в production
```

### ⚠️ Проблемы производительности

#### 1. Отсутствие кэширования запросов

**Нет кэширования на уровне приложения**
```python
# ПРОБЛЕМА: Каждый запрос идет в БД
async def search_products(session: AsyncSession, query: str):
    # Нет кэширования результатов поиска

# РЕШЕНИЕ: Добавить Redis кэш
@cache(ttl=300)  # 5 минут
async def search_products_cached(query: str) -> list[Product]:
    # Кэшированный поиск
```

**Повторные запросы пользователей**
```python
# ПРОБЛЕМА: get_current_auth_user вызывается на каждом запросе
async def get_current_auth_user(token: str, session: AsyncSession):
    user = await get_user_by_uid(session, uid)  # БД запрос каждый раз

# РЕШЕНИЕ: Кэширование пользователя в Redis
async def get_cached_user(uid: str) -> UserResponse:
    cached = await redis.get(f"user:{uid}")
    if cached:
        return UserResponse.model_validate_json(cached)
    # Загрузить из БД и кэшировать
```

#### 2. N+1 запросы

**Потенциальные N+1 в продуктах**
```python
# ПРОБЛЕМА: При загрузке списка продуктов
products = await session.execute(select(Product))
for product in products:
    # Может вызывать дополнительные запросы для nutrients
    nutrients = product.nutrient_associations
```

**Решение с prefetch**
```python
# РЕШЕНИЕ: Использовать selectinload
stmt = select(Product).options(
    selectinload(Product.nutrient_associations).selectinload(ProductNutrient.nutrients),
    joinedload(Product.product_groups)
)
```

#### 3. Неоптимальные индексы

**Отсутствующие составные индексы**
```python
# ПРОБЛЕМА: Поиск по нескольким полям
# WHERE is_active = true AND created_at > '...' AND role = 'user'

# ДОБАВИТЬ составные индексы:
Index("idx_users_active_created", "is_active", "created_at")
Index("idx_users_active_role", "is_active", "role")
Index("idx_products_group_active", "group_id", "is_active")
```

**Неиспользуемые индексы**
```python
# Проверить использование существующих индексов
# SELECT * FROM pg_stat_user_indexes WHERE schemaname = 'public';
```

#### 4. Отсутствие пагинации

**Загрузка всех результатов**
```python
# ПРОБЛЕМА: Возврат всех найденных продуктов
async def search_products(query: str) -> list[Product]:
    # Может вернуть тысячи записей

# РЕШЕНИЕ: Добавить пагинацию
async def search_products(
    query: str,
    offset: int = 0,
    limit: int = 20
) -> tuple[list[Product], int]:
    # LIMIT/OFFSET + COUNT для total
```

#### 5. Мониторинг производительности

**Отсутствие профилирования**
```python
# ОТСУТСТВУЕТ:
- APM (Application Performance Monitoring)
- Slow query logging
- Request timing middleware
- Memory usage monitoring
- Connection pool monitoring
```

### 🔧 Рекомендуемые улучшения

#### 1. Реализовать кэширование
```python
# cache/redis_cache.py
class CacheService:
    def __init__(self, redis: Redis):
        self.redis = redis

    async def get_or_set(
        self,
        key: str,
        factory: Callable[[], Awaitable[T]],
        ttl: int = 300
    ) -> T:
        cached = await self.redis.get(key)
        if cached:
            return json.loads(cached)

        result = await factory()
        await self.redis.setex(key, ttl, json.dumps(result, default=str))
        return result

# Применение в сервисах
class ProductService:
    async def search_products(self, query: str) -> list[Product]:
        return await self.cache.get_or_set(
            f"search:{hash(query)}",
            lambda: self._search_products_db(query),
            ttl=600  # 10 минут
        )
```

#### 2. Добавить middleware для профилирования
```python
# middleware/performance.py
class PerformanceMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()

        response = await call_next(request)

        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)

        # Логирование медленных запросов
        if process_time > 1.0:  # > 1 секунды
            log.warning("Slow request: %s %s took %.2fs",
                       request.method, request.url, process_time)

        # Метрики в Prometheus
        request_duration.labels(
            method=request.method,
            endpoint=request.url.path
        ).observe(process_time)

        return response
```

#### 3. Оптимизировать БД запросы
```python
# crud/optimized.py
class OptimizedProductCRUD:
    async def search_with_facets(
        self,
        session: AsyncSession,
        query: str,
        category_id: int = None,
        offset: int = 0,
        limit: int = 20
    ) -> tuple[list[Product], dict]:

        # Основной запрос с фильтрами
        stmt = select(Product).options(
            joinedload(Product.product_groups),
            selectinload(Product.nutrient_associations)
        )

        if query:
            stmt = stmt.filter(Product.search_vector.match(query))
        if category_id:
            stmt = stmt.filter(Product.group_id == category_id)

        # Пагинация
        stmt = stmt.offset(offset).limit(limit)

        # Выполнение запроса
        result = await session.execute(stmt)
        products = result.unique().scalars().all()

        # Facets для фильтрации (параллельно)
        facets = await self._get_search_facets(session, query)

        return products, facets

    async def _get_search_facets(self, session: AsyncSession, query: str) -> dict:
        # Агрегация по категориям
        facet_stmt = select(
            ProductGroup.name,
            func.count(Product.id).label('count')
        ).join(Product.product_groups).group_by(ProductGroup.name)

        if query:
            facet_stmt = facet_stmt.filter(Product.search_vector.match(query))

        result = await session.execute(facet_stmt)
        return {"categories": dict(result.all())}
```

#### 4. Добавить connection pool мониторинг
```python
# core/db_helper.py
class DatabaseHelper:
    def __init__(self):
        self.engine = create_async_engine(
            settings.effective_db_url,
            echo=settings.db.echo,
            pool_size=settings.db.pool_size,
            max_overflow=settings.db.max_overflow,
            pool_pre_ping=True,  # Проверка соединений
            pool_recycle=3600,   # Переподключение каждый час
        )

        # Метрики pool
        self.setup_pool_metrics()

    def setup_pool_metrics(self):
        @event.listens_for(self.engine.sync_engine, "connect")
        def receive_connect(dbapi_connection, connection_record):
            connection_pool_size.inc()

        @event.listens_for(self.engine.sync_engine, "close")
        def receive_close(dbapi_connection, connection_record):
            connection_pool_size.dec()
```

#### 5. Реализовать фоновые задачи для подогрева кэша
```python
# tasks/cache_warmup.py
@broker.task(cron="0 */6 * * *")  # Каждые 6 часов
async def warmup_popular_searches():
    """Предварительная загрузка популярных поисковых запросов"""
    popular_queries = [
        "молоко", "хлеб", "мясо", "овощи", "фрукты"
    ]

    async with db_helper.session_getter() as session:
        for query in popular_queries:
            await search_products_cached(session, query)

@broker.task(cron="0 2 * * *")  # Каждый день в 2:00
async def cleanup_expired_cache():
    """Очистка устаревшего кэша"""
    await redis.flushdb()  # Или selective cleanup
```

### 📊 Benchmarking и мониторинг

#### 1. Добавить метрики Prometheus
```python
# metrics/prometheus.py
from prometheus_client import Counter, Histogram, Gauge

# Request metrics
request_count = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

request_duration = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration',
    ['method', 'endpoint']
)

# Database metrics
db_query_duration = Histogram(
    'db_query_duration_seconds',
    'Database query duration',
    ['operation']
)

# Cache metrics
cache_hits = Counter('cache_hits_total', 'Cache hits', ['cache_type'])
cache_misses = Counter('cache_misses_total', 'Cache misses', ['cache_type'])

# Active connections
active_connections = Gauge('db_active_connections', 'Active DB connections')
```

#### 2. Настроить алерты
```yaml
# prometheus/alerts.yml
groups:
  - name: nutricoreiq
    rules:
      - alert: HighResponseTime
        expr: http_request_duration_seconds{quantile="0.95"} > 2
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High response time detected"

      - alert: DatabaseConnectionPoolExhausted
        expr: db_active_connections >= 45  # 90% of pool_size
        for: 2m
        labels:
          severity: critical
```

#### 3. Load testing
```python
# tests/load/locustfile.py
from locust import HttpUser, task, between

class NutriCoreIQUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        # Логин пользователя
        self.client.post("/api/v1/auth/login", json={
            "username": "testuser",
            "password": "testpass123"
        })

    @task(3)
    def search_products(self):
        self.client.get("/api/v1/product/search?query=молоко")

    @task(1)
    def get_product_details(self):
        self.client.get("/api/v1/product/1")

    @task(1)
    def get_profile(self):
        self.client.get("/api/v1/user/profile")
```

### 🎯 Performance targets

#### Текущие показатели (оценочно)
- **Response time (p95)**: ~500ms
- **Throughput**: ~100 RPS
- **Cache hit ratio**: 0% (нет кэша)
- **Database connections**: 10-15 active

#### Целевые показатели
- **Response time (p95)**: <200ms
- **Throughput**: >500 RPS
- **Cache hit ratio**: >80%
- **Database connections**: <30 active

### 🔍 Профилирование

#### 1. SQL запросы
```python
# Включить логирование медленных запросов
# postgresql.conf
log_min_duration_statement = 1000  # >1 секунды

# В коде добавить timing
@event.listens_for(Engine, "before_cursor_execute")
def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    context._query_start_time = time.time()

@event.listens_for(Engine, "after_cursor_execute")
def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    total = time.time() - context._query_start_time
    if total > 0.1:  # >100ms
        log.warning("Slow query: %.2fs - %s", total, statement[:100])
```

#### 2. Memory profiling
```python
# middleware/memory.py
import psutil
import os

class MemoryMonitoringMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        process = psutil.Process(os.getpid())
        memory_before = process.memory_info().rss

        response = await call_next(request)

        memory_after = process.memory_info().rss
        memory_diff = memory_after - memory_before

        if memory_diff > 10 * 1024 * 1024:  # >10MB
            log.warning("High memory usage: %s %s used %dMB",
                       request.method, request.url, memory_diff // 1024 // 1024)

        return response
```

### 📈 Оптимизация по приоритетам

#### 1. Высокий приоритет (1-2 недели)
- Добавить Redis кэширование для поиска продуктов
- Реализовать кэширование текущего пользователя
- Добавить пагинацию к API endpoints
- Создать составные индексы БД

#### 2. Средний приоритет (1 месяц)
- Внедрить performance middleware с метриками
- Настроить connection pool monitoring
- Добавить prefetch для связанных данных
- Реализовать фоновые задачи для кэша

#### 3. Низкий приоритет (2-3 месяца)
- Настроить CDN для статических файлов
- Реализовать партиционирование больших таблиц
- Добавить read replicas для БД
- Настроить advanced caching strategies

**Итог**: Архитектура проекта хорошо подходит для высокой производительности, но требует добавления кэширования, мониторинга и оптимизации БД запросов для достижения production-ready показателей.
