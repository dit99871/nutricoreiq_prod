# Анализ src/app/models/user.py

## Критические проблемы

### 1. Неправильное использование default для UUID (строка 15)
```python
# ОШИБКА: UUID генерируется в момент импорта модуля, а не создания записи
uid: Mapped[str] = mapped_column(default=str(uuid4()))

# ИСПРАВЛЕНИЕ: Использовать default_factory
uid: Mapped[str] = mapped_column(default_factory=lambda: str(uuid4()))

# ИЛИ ЛУЧШЕ: Добавить индекс для производительности
uid: Mapped[str] = mapped_column(
    default_factory=lambda: str(uuid4()),
    unique=True,
    index=True
)
```

### 2. Хранение даты как строки (строки 32-34)
```python
# ОШИБКА: Дата как строка + вычисление в момент импорта
created_at: Mapped[str] = mapped_column(
    default=dt.datetime.now(dt.UTC).strftime("%d.%m.%Y %H:%M:%S")
)

# ИСПРАВЛЕНИЕ: Использовать datetime и default_factory
from datetime import datetime

created_at: Mapped[datetime] = mapped_column(
    default_factory=lambda: dt.datetime.now(dt.UTC),
    index=True  # Для сортировки по дате
)
```

### 3. Отсутствующие индексы для важных полей
```python
# ПРОБЛЕМА: Поля без индексов, которые используются в запросах
is_active: Mapped[bool] = mapped_column(default=True)
role: Mapped[str] = mapped_column(default="user")

# ИСПРАВЛЕНИЕ: Добавить индексы
is_active: Mapped[bool] = mapped_column(default=True, index=True)
role: Mapped[str] = mapped_column(default="user", index=True)
```

## Проблемы проектирования

### 1. Примитивные типы вместо Value Objects
```python
# ПРОБЛЕМА: Строки без валидации
role: Mapped[str] = mapped_column(default="user")
kfa: Mapped[Literal["1", "2", "3", "4", "5"]] = mapped_column(nullable=True)

# РЕКОМЕНДАЦИЯ: Использовать Enum
from enum import Enum

class UserRole(str, Enum):
    USER = "user"
    ADMIN = "admin"
    MODERATOR = "moderator"

class KFALevel(str, Enum):
    VERY_LOW = "1"
    LOW = "2"
    MEDIUM = "3"
    HIGH = "4"
    VERY_HIGH = "5"

# В модели:
role: Mapped[UserRole] = mapped_column(default=UserRole.USER, index=True)
kfa: Mapped[KFALevel | None] = mapped_column(nullable=True)
```

### 2. Отсутствие ограничений базы данных
```python
# ДОБАВИТЬ: CHECK constraints для валидации
from sqlalchemy import CheckConstraint

class User(IntIdPkMixin, Base):
    # ... поля ...

    __table_args__ = (
        CheckConstraint("age > 0 AND age < 150", name="valid_age"),
        CheckConstraint("weight > 0 AND weight < 1000", name="valid_weight"),
        CheckConstraint("height > 0 AND height < 300", name="valid_height"),
        CheckConstraint(
            "email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'",
            name="valid_email"
        ),
    )
```

### 3. Отсутствие поля updated_at
```python
# ДОБАВИТЬ: Поле для отслеживания изменений
updated_at: Mapped[datetime | None] = mapped_column(
    default=None,
    onupdate=lambda: dt.datetime.now(dt.UTC),
    index=True
)
```

## Полное исправленное решение

```python
import datetime as dt
from datetime import datetime
from typing import Literal
from uuid import uuid4
from enum import Enum

from sqlalchemy import CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .mixins import IntIdPkMixin
from .base import Base


class UserRole(str, Enum):
    USER = "user"
    ADMIN = "admin"
    MODERATOR = "moderator"


class KFALevel(str, Enum):
    VERY_LOW = "1"
    LOW = "2"
    MEDIUM = "3"
    HIGH = "4"
    VERY_HIGH = "5"


class GoalType(str, Enum):
    LOSE_WEIGHT = "Снижение веса"
    GAIN_WEIGHT = "Увеличение веса"
    MAINTAIN_WEIGHT = "Поддержание веса"


class User(IntIdPkMixin, Base):
    # Уникальные поля с индексами
    uid: Mapped[str] = mapped_column(
        default_factory=lambda: str(uuid4()),
        unique=True,
        index=True
    )
    username: Mapped[str] = mapped_column(unique=True, index=True)
    email: Mapped[str] = mapped_column(unique=True, index=True)
    hashed_password: Mapped[bytes]

    # Профильные данные
    gender: Mapped[Literal["female", "male"] | None] = mapped_column(nullable=True)
    age: Mapped[int | None] = mapped_column(nullable=True)
    weight: Mapped[float | None] = mapped_column(nullable=True)
    height: Mapped[float | None] = mapped_column(nullable=True)
    kfa: Mapped[KFALevel | None] = mapped_column(nullable=True)
    goal: Mapped[GoalType | None] = mapped_column(nullable=True)

    # Статусные поля с индексами
    is_subscribed: Mapped[bool] = mapped_column(default=True)
    is_active: Mapped[bool] = mapped_column(default=True, index=True)
    role: Mapped[UserRole] = mapped_column(default=UserRole.USER, index=True)

    # Временные метки
    created_at: Mapped[datetime] = mapped_column(
        default_factory=lambda: dt.datetime.now(dt.UTC),
        index=True
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        default=None,
        onupdate=lambda: dt.datetime.now(dt.UTC)
    )

    # Ограничения БД
    __table_args__ = (
        CheckConstraint("age > 0 AND age < 150", name="valid_age"),
        CheckConstraint("weight > 0 AND weight < 1000", name="valid_weight"),
        CheckConstraint("height > 0 AND height < 300", name="valid_height"),
        CheckConstraint(
            "email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'",
            name="valid_email"
        ),
    )
```

## Необходимая миграция

```python
# Создать новую миграцию для исправления проблем
def upgrade() -> None:
    # 1. Изменить тип created_at
    op.add_column('users', sa.Column('created_at_new', sa.DateTime(), nullable=True))

    # 2. Конвертировать существующие данные
    op.execute("""
        UPDATE users
        SET created_at_new = TO_TIMESTAMP(created_at, 'DD.MM.YYYY HH24:MI:SS')
        WHERE created_at IS NOT NULL
    """)

    # 3. Удалить старую колонку и переименовать новую
    op.drop_column('users', 'created_at')
    op.alter_column('users', 'created_at_new', new_column_name='created_at')

    # 4. Добавить недостающие индексы
    op.create_index('ix_users_uid', 'users', ['uid'], unique=True)
    op.create_index('ix_users_is_active', 'users', ['is_active'])
    op.create_index('ix_users_role', 'users', ['role'])
    op.create_index('ix_users_created_at', 'users', ['created_at'])

    # 5. Добавить CHECK constraints
    op.create_check_constraint('valid_age', 'users', 'age > 0 AND age < 150')
    op.create_check_constraint('valid_weight', 'users', 'weight > 0 AND weight < 1000')
    op.create_check_constraint('valid_height', 'users', 'height > 0 AND height < 300')
```

## Приоритет исправлений

1. **Критический**: Исправить UUID default и created_at тип данных
2. **Высокий**: Добавить недостающие индексы
3. **Средний**: Использовать Enum вместо строк
4. **Низкий**: Добавить CHECK constraints и updated_at
