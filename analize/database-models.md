# Анализ моделей базы данных - NutriCoreIQ

## Общая оценка: 7/10

### ✅ Хорошие решения

#### 1. Использование современного SQLAlchemy 2.0
```python
# Правильное использование Mapped и mapped_column
class User(IntIdPkMixin, Base):
    username: Mapped[str] = mapped_column(unique=True, index=True)
    email: Mapped[str] = mapped_column(unique=True, index=True)
```

#### 2. Хорошая организация моделей
- **Базовая модель**: `Base` с автоматическим именованием таблиц
- **Миксины**: `IntIdPkMixin` для первичных ключей
- **Соглашения по именованию**: Автоматическое преобразование CamelCase → snake_case

#### 3. Правильная настройка связей
```python
# Product.py - хорошие связи с lazy loading
product_groups: Mapped["ProductGroup"] = relationship(
    back_populates="products", lazy="joined"
)
nutrient_associations: Mapped[list["ProductNutrient"]] = relationship(
    back_populates="products", lazy="selectin"
)
```

#### 4. Использование индексов
```python
# Product.py - оптимизация для поиска
Index("idx_product_search_vector", search_vector, postgresql_using="gin")
Index("idx_product_title_trgm", title, postgresql_using="gin",
      postgresql_ops={"title": "gin_trgm_ops"})
```

#### 5. PostgreSQL-специфичные возможности
```python
# Полнотекстовый поиск
search_vector: Mapped[TSVECTOR] = mapped_column(TSVECTOR())
```

### ⚠️ Серьезные проблемы

#### 1. Критические ошибки в модели User

**Проблема с UUID**
```python
# ОШИБКА: UUID генерируется в момент импорта модуля
uid: Mapped[str] = mapped_column(default=str(uuid4()))

# ИСПРАВЛЕНИЕ:
uid: Mapped[str] = mapped_column(default_factory=lambda: str(uuid4()))
# ИЛИ ЛУЧШЕ:
uid: Mapped[str] = mapped_column(default_factory=lambda: str(uuid4()), unique=True, index=True)
```

**Проблема с датой создания**
```python
# ОШИБКА: Дата как строка + вычисление в момент импорта
created_at: Mapped[str] = mapped_column(
    default=dt.datetime.now(dt.UTC).strftime("%d.%m.%Y %H:%M:%S")
)

# ИСПРАВЛЕНИЕ:
created_at: Mapped[datetime] = mapped_column(
    default_factory=lambda: dt.datetime.now(dt.UTC)
)
```

#### 2. Отсутствующие индексы

**User модель**
```python
# ОТСУТСТВУЮТ:
- uid (уникальный индекс) ❌
- created_at (для сортировки по дате) ❌
- is_active (для фильтрации) ❌

# ДОБАВИТЬ:
uid: Mapped[str] = mapped_column(unique=True, index=True, default_factory=lambda: str(uuid4()))
created_at: Mapped[datetime] = mapped_column(default_factory=lambda: dt.datetime.now(dt.UTC), index=True)
is_active: Mapped[bool] = mapped_column(default=True, index=True)
```

**ProductNutrient модель**
```python
# ПРОБЛЕМА: Составной первичный ключ но также наследует IntIdPkMixin
class ProductNutrient(IntIdPkMixin, Base):
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), primary_key=True)
    nutrient_id: Mapped[int] = mapped_column(ForeignKey("nutrients.id"), primary_key=True)

# ИСПРАВЛЕНИЕ: Убрать IntIdPkMixin, использовать только составной ключ
class ProductNutrient(Base):
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), primary_key=True)
    nutrient_id: Mapped[int] = mapped_column(ForeignKey("nutrients.id"), primary_key=True)
    amount: Mapped[float] = mapped_column(default=0.0)
```

#### 3. Проблемы с типами данных

**Неоптимальные типы в User**
```python
# ПРОБЛЕМА: kfa как строка вместо enum
kfa: Mapped[Literal["1", "2", "3", "4", "5"]] = mapped_column(nullable=True)

# ЛУЧШЕ: Использовать Enum
class KFALevel(Enum):
    VERY_LOW = "1"    # Очень низкий
    LOW = "2"         # Низкий
    MEDIUM = "3"      # Средний
    HIGH = "4"        # Высокий
    VERY_HIGH = "5"   # Очень высокий

kfa: Mapped[KFALevel | None] = mapped_column(nullable=True)
```

**Проблема с ролями**
```python
# ПРОБЛЕМА: role как строка без ограничений
role: Mapped[str] = mapped_column(default="user")

# ЛУЧШЕ:
class UserRole(Enum):
    USER = "user"
    ADMIN = "admin"
    MODERATOR = "moderator"

role: Mapped[UserRole] = mapped_column(default=UserRole.USER)
```

#### 4. Отсутствующие ограничения

**Валидация email**
```python
# ДОБАВИТЬ CHECK constraints
__table_args__ = (
    CheckConstraint("email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'", name="valid_email"),
    CheckConstraint("age > 0 AND age < 150", name="valid_age"),
    CheckConstraint("weight > 0 AND weight < 1000", name="valid_weight"),
    CheckConstraint("height > 0 AND height < 300", name="valid_height"),
)
```

### 🔧 Рекомендуемые улучшения

#### 1. Исправить модель User
```python
import datetime as dt
from enum import Enum
from uuid import uuid4
from sqlalchemy import CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column

class UserRole(Enum):
    USER = "user"
    ADMIN = "admin"
    MODERATOR = "moderator"

class KFALevel(Enum):
    VERY_LOW = "1"
    LOW = "2"
    MEDIUM = "3"
    HIGH = "4"
    VERY_HIGH = "5"

class GoalType(Enum):
    LOSE_WEIGHT = "Снижение веса"
    GAIN_WEIGHT = "Увеличение веса"
    MAINTAIN_WEIGHT = "Поддержание веса"

class User(IntIdPkMixin, Base):
    uid: Mapped[str] = mapped_column(
        unique=True,
        index=True,
        default_factory=lambda: str(uuid4())
    )
    username: Mapped[str] = mapped_column(unique=True, index=True)
    email: Mapped[str] = mapped_column(unique=True, index=True)
    hashed_password: Mapped[bytes]

    gender: Mapped[Literal["female", "male"] | None] = mapped_column(nullable=True)
    age: Mapped[int | None] = mapped_column(nullable=True)
    weight: Mapped[float | None] = mapped_column(nullable=True)
    height: Mapped[float | None] = mapped_column(nullable=True)
    kfa: Mapped[KFALevel | None] = mapped_column(nullable=True)
    goal: Mapped[GoalType | None] = mapped_column(nullable=True)

    is_subscribed: Mapped[bool] = mapped_column(default=True)
    is_active: Mapped[bool] = mapped_column(default=True, index=True)
    role: Mapped[UserRole] = mapped_column(default=UserRole.USER)

    created_at: Mapped[datetime] = mapped_column(
        default_factory=lambda: dt.datetime.now(dt.UTC),
        index=True
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        default=None,
        onupdate=lambda: dt.datetime.now(dt.UTC)
    )

    __table_args__ = (
        CheckConstraint("age > 0 AND age < 150", name="valid_age"),
        CheckConstraint("weight > 0 AND weight < 1000", name="valid_weight"),
        CheckConstraint("height > 0 AND height < 300", name="valid_height"),
        CheckConstraint("email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'", name="valid_email"),
    )
```

#### 2. Исправить ProductNutrient
```python
class ProductNutrient(Base):
    __tablename__ = "product_nutrients"  # Явное именование

    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"),
        primary_key=True
    )
    nutrient_id: Mapped[int] = mapped_column(
        ForeignKey("nutrients.id", ondelete="CASCADE"),
        primary_key=True
    )
    amount: Mapped[float] = mapped_column(default=0.0)

    products: Mapped["Product"] = relationship(back_populates="nutrient_associations")
    nutrients: Mapped["Nutrient"] = relationship(back_populates="product_associations")

    __table_args__ = (
        CheckConstraint("amount >= 0", name="positive_amount"),
    )
```

#### 3. Добавить аудит модели
```python
class AuditMixin:
    created_at: Mapped[datetime] = mapped_column(
        default_factory=lambda: dt.datetime.now(dt.UTC),
        index=True
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        default=None,
        onupdate=lambda: dt.datetime.now(dt.UTC)
    )

# Применить ко всем основным моделям
class Product(IntIdPkMixin, AuditMixin, Base):
    # ...
```

#### 4. Добавить модель для логирования изменений
```python
class UserActivityLog(IntIdPkMixin, Base):
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(index=True)
    details: Mapped[dict] = mapped_column(JSON)
    ip_address: Mapped[str | None] = mapped_column(nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        default_factory=lambda: dt.datetime.now(dt.UTC),
        index=True
    )
```

### 📊 Анализ производительности

#### Индексы
- **Существующие**: username, email, product search (GIN)
- **Отсутствующие**: uid, is_active, created_at, role
- **Избыточные**: Нет

#### Связи
- **N+1 проблемы**: Частично решены через lazy="selectin"
- **Eager loading**: Настроено для product_groups
- **Оптимизация**: Хорошая для чтения, нужна для записи

### 🎯 Миграции

Необходимые миграции для исправления проблем:

```python
# alembic migration
def upgrade() -> None:
    # Исправить uid column
    op.alter_column('users', 'uid', type_=sa.String(), unique=True)
    op.create_index('ix_users_uid', 'users', ['uid'])

    # Исправить created_at
    op.add_column('users', sa.Column('created_at_new', sa.DateTime(), nullable=True))
    # Конвертировать существующие данные
    # Удалить старую колонку, переименовать новую

    # Добавить недостающие индексы
    op.create_index('ix_users_is_active', 'users', ['is_active'])
    op.create_index('ix_users_created_at', 'users', ['created_at'])

    # Добавить CHECK constraints
    op.create_check_constraint('valid_age', 'users', 'age > 0 AND age < 150')
    op.create_check_constraint('valid_weight', 'users', 'weight > 0 AND weight < 1000')
```

### 🔍 Отсутствующие модели

Рекомендуется добавить:

1. **UserSession** - для управления сессиями
2. **UserActivityLog** - логирование действий
3. **ProductReview** - отзывы о продуктах
4. **UserFavorites** - избранные продукты
5. **NutritionPlan** - планы питания

### 📈 Рекомендации по производительности

#### 1. Партиционирование
```sql
-- Для больших таблиц логов
CREATE TABLE user_activity_log_2024 PARTITION OF user_activity_log
FOR VALUES FROM ('2024-01-01') TO ('2025-01-01');
```

#### 2. Материализованные представления
```sql
-- Для аналитики продуктов
CREATE MATERIALIZED VIEW popular_products AS
SELECT product_id, COUNT(*) as views
FROM product_views
GROUP BY product_id;
```

**Итог**: Модели имеют хорошую структуру, но содержат критические ошибки, которые необходимо немедленно исправить. После исправления база данных будет готова к production использованию.
