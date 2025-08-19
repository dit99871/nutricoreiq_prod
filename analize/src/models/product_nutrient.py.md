# Анализ src/app/models/product_nutrient.py

## Критические проблемы

### 1. Конфликт наследования (строка 8)
```python
# ПРОБЛЕМА: Наследует IntIdPkMixin и использует composite primary key
class ProductNutrient(IntIdPkMixin, Base):
    amount: Mapped[float] = mapped_column(default=0.0)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id"),
        primary_key=True,  # Конфликт с IntIdPkMixin.id
    )
    nutrient_id: Mapped[int] = mapped_column(
        ForeignKey("nutrients.id"),
        primary_key=True,  # Конфликт с IntIdPkMixin.id
    )
```

**Исправление:**
```python
# РЕШЕНИЕ 1: Убрать IntIdPkMixin, использовать только составной ключ
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

# РЕШЕНИЕ 2: Оставить auto-increment ID (если нужен для ORM)
class ProductNutrient(IntIdPkMixin, Base):
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"),
        index=True  # Убрать primary_key=True
    )
    nutrient_id: Mapped[int] = mapped_column(
        ForeignKey("nutrients.id", ondelete="CASCADE"),
        index=True  # Убрать primary_key=True
    )
    amount: Mapped[float] = mapped_column(default=0.0)

    # Добавить уникальный составной индекс
    __table_args__ = (
        Index("ix_product_nutrient_unique", "product_id", "nutrient_id", unique=True),
        CheckConstraint("amount >= 0", name="positive_amount"),
    )
```

### 2. Отсутствие CASCADE для внешних ключей
```python
# ПРОБЛЕМА: При удалении продукта/питательного вещества остаются orphan записи
ForeignKey("products.id")
ForeignKey("nutrients.id")

# ИСПРАВЛЕНИЕ: Добавить CASCADE
ForeignKey("products.id", ondelete="CASCADE")
ForeignKey("nutrients.id", ondelete="CASCADE")
```

### 3. Отсутствие валидации данных
```python
# ПРОБЛЕМА: amount может быть отрицательным
amount: Mapped[float] = mapped_column(default=0.0)

# ИСПРАВЛЕНИЕ: Добавить CHECK constraint
from sqlalchemy import CheckConstraint

__table_args__ = (
    CheckConstraint("amount >= 0", name="positive_amount"),
)
```

## Рекомендации по улучшению

### 1. Добавить метаданные
```python
from datetime import datetime
import datetime as dt

class ProductNutrient(Base):
    # ... основные поля ...

    # Метаданные для аудита
    created_at: Mapped[datetime] = mapped_column(
        default_factory=lambda: dt.datetime.now(dt.UTC)
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        default=None,
        onupdate=lambda: dt.datetime.now(dt.UTC)
    )

    # Источник данных (опционально)
    source: Mapped[str | None] = mapped_column(nullable=True)  # "usda", "manual", etc.
```

### 2. Добавить методы для бизнес-логики
```python
class ProductNutrient(Base):
    # ... поля ...

    @property
    def amount_per_100g(self) -> float:
        """Количество питательного вещества на 100г продукта"""
        return self.amount

    def calculate_amount_for_weight(self, weight_grams: float) -> float:
        """Рассчитать количество питательного вещества для заданного веса"""
        return (self.amount * weight_grams) / 100

    @classmethod
    async def get_nutrition_for_product(
        cls,
        session: AsyncSession,
        product_id: int
    ) -> list["ProductNutrient"]:
        """Получить все питательные вещества для продукта"""
        stmt = select(cls).where(cls.product_id == product_id)
        result = await session.execute(stmt)
        return result.scalars().all()
```

### 3. Улучшить связи
```python
class ProductNutrient(Base):
    # ... поля ...

    # Более точные связи
    product: Mapped["Product"] = relationship(
        "Product",
        back_populates="nutrient_associations",
        lazy="select"  # Оптимизация загрузки
    )
    nutrient: Mapped["Nutrient"] = relationship(
        "Nutrient",
        back_populates="product_associations",
        lazy="select"
    )
```

## Полное исправленное решение

```python
from datetime import datetime
import datetime as dt
from sqlalchemy import ForeignKey, CheckConstraint, Index
from sqlalchemy.orm import mapped_column, Mapped, relationship
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from .base import Base


class ProductNutrient(Base):
    __tablename__ = "product_nutrients"

    # Составной первичный ключ
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"),
        primary_key=True
    )
    nutrient_id: Mapped[int] = mapped_column(
        ForeignKey("nutrients.id", ondelete="CASCADE"),
        primary_key=True
    )

    # Основные данные
    amount: Mapped[float] = mapped_column(default=0.0)  # на 100г продукта

    # Метаданные
    source: Mapped[str | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        default_factory=lambda: dt.datetime.now(dt.UTC)
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        default=None,
        onupdate=lambda: dt.datetime.now(dt.UTC)
    )

    # Связи
    product: Mapped["Product"] = relationship(
        "Product",
        back_populates="nutrient_associations"
    )
    nutrient: Mapped["Nutrient"] = relationship(
        "Nutrient",
        back_populates="product_associations"
    )

    # Ограничения
    __table_args__ = (
        CheckConstraint("amount >= 0", name="positive_amount"),
        Index("ix_product_nutrient_amount", "amount"),
        Index("ix_product_nutrient_created", "created_at"),
    )

    # Бизнес-методы
    def calculate_amount_for_weight(self, weight_grams: float) -> float:
        """Рассчитать количество питательного вещества для заданного веса"""
        if weight_grams <= 0:
            return 0.0
        return (self.amount * weight_grams) / 100

    @classmethod
    async def get_nutrition_summary(
        cls,
        session: AsyncSession,
        product_id: int
    ) -> dict[str, float]:
        """Получить сводку по питательным веществам для продукта"""
        stmt = (
            select(cls)
            .options(selectinload(cls.nutrient))
            .where(cls.product_id == product_id)
        )
        result = await session.execute(stmt)
        nutrients = result.scalars().all()

        return {
            nutrient.nutrient.name: nutrient.amount
            for nutrient in nutrients
        }

    def __repr__(self) -> str:
        return (
            f"<ProductNutrient(product_id={self.product_id}, "
            f"nutrient_id={self.nutrient_id}, amount={self.amount})>"
        )
```

## Необходимая миграция

```python
def upgrade() -> None:
    # Если используется Решение 1 (без IntIdPkMixin):

    # 1. Создать новую таблицу с правильной структурой
    op.create_table(
        'product_nutrients_new',
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('nutrient_id', sa.Integer(), nullable=False),
        sa.Column('amount', sa.Float(), nullable=False, default=0.0),
        sa.Column('source', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['nutrient_id'], ['nutrients.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('product_id', 'nutrient_id'),
        sa.CheckConstraint('amount >= 0', name='positive_amount')
    )

    # 2. Скопировать данные
    op.execute("""
        INSERT INTO product_nutrients_new (product_id, nutrient_id, amount, created_at)
        SELECT product_id, nutrient_id, amount, NOW()
        FROM product_nutrients
    """)

    # 3. Удалить старую таблицу и переименовать новую
    op.drop_table('product_nutrients')
    op.rename_table('product_nutrients_new', 'product_nutrients')

    # 4. Создать индексы
    op.create_index('ix_product_nutrient_amount', 'product_nutrients', ['amount'])
    op.create_index('ix_product_nutrient_created', 'product_nutrients', ['created_at'])
```

## Приоритет исправлений

1. **Критический**: Исправить конфликт primary key (выбрать одно из решений)
2. **Высокий**: Добавить CASCADE для внешних ключей
3. **Средний**: Добавить CHECK constraint для amount
4. **Низкий**: Добавить метаданные и бизнес-методы
