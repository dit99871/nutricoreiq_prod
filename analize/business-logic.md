# Анализ бизнес-логики - NutriCoreIQ

## Общая оценка: 7/10

### ✅ Хорошие решения бизнес-логики

#### 1. Четкое разделение ответственности
```python
# Правильная организация слоев:
- models/     # Модели данных
- schemas/    # Валидация данных
- crud/       # Операции с БД
- routers/    # API endpoints
- services/   # Бизнес-логика
- utils/      # Вспомогательные функции
```

#### 2. Валидация данных с Pydantic
```python
# schemas/user.py - хорошая валидация
class UserCreate(UserBase):
    password: Annotated[str, MinLen(8)]  # Минимальная длина пароля

class UserProfile(BaseSchema):
    age: int = Field(gt=0)          # Положительный возраст
    weight: float = Field(gt=0)     # Положительный вес
    height: float = Field(gt=0)     # Положительный рост
```

#### 3. Обработка ошибок
```python
# Структурированная обработка ошибок
CREDENTIAL_EXCEPTION = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail={"message": "Ошибка аутентификации. Пожалуйста, войдите заново"},
    headers={"WWW-Authenticate": "Bearer"},
)

# Централизованные exception handlers
def http_exception_handler(request: Request, exc: HTTPException):
    # Единообразная структура ответов об ошибках
```

#### 4. Асинхронные задачи
```python
# tasks/welcome_email_notification.py
@broker.task(max_retries=3, retry_delay=60)
async def send_welcome_email(user_email: EmailStr, session: AsyncSession):
    # Отправка приветственного письма в фоне
    # С правильной обработкой ошибок и retry логикой
```

#### 5. Безопасность данных
```python
# Хеширование паролей
def get_password_hash(password: str) -> bytes:
    return pwd_context.hash(password).encode("utf-8")

# JWT токены с RSA ключами
# Проверка прав доступа через Depends
```

### ⚠️ Проблемы бизнес-логики

#### 1. Отсутствие доменных сервисов

**Бизнес-логика разбросана**
```python
# ПРОБЛЕМА: Логика в разных слоях
# В роутерах:
@router.post("/register")
async def register_user(user_in: UserCreate, session: AsyncSession):
    # Проверка существования пользователя
    existing_user = await get_user_by_email(session, user_in.email)
    if existing_user:
        raise HTTPException(...)

    # Создание пользователя
    user = await create_user(session, user_in)

    # Отправка email
    await send_welcome_email.kiq(user.email)

# РЕШЕНИЕ: Доменный сервис
class UserService:
    async def register_user(self, user_data: UserCreate) -> UserResponse:
        # Вся бизнес-логика регистрации в одном месте
        await self._validate_unique_user(user_data)
        user = await self._create_user(user_data)
        await self._send_welcome_email(user)
        return user
```

#### 2. Недостаточная валидация бизнес-правил

**Отсутствие сложных валидаций**
```python
# ПРОБЛЕМА: Только базовая валидация в схемах
class UserProfile(BaseSchema):
    age: int = Field(gt=0)
    weight: float = Field(gt=0)
    height: float = Field(gt=0)

# РЕШЕНИЕ: Бизнес-валидаторы
class UserProfileValidator:
    @staticmethod
    def validate_health_metrics(age: int, weight: float, height: float) -> list[str]:
        errors = []

        # BMI проверка
        bmi = weight / (height/100) ** 2
        if bmi < 16 or bmi > 40:
            errors.append("BMI вне допустимого диапазона")

        # Возрастные ограничения
        if age < 16:
            errors.append("Минимальный возраст 16 лет")
        elif age > 100:
            errors.append("Максимальный возраст 100 лет")

        return errors
```

#### 3. Отсутствие бизнес-событий

**Нет событийной модели**
```python
# ПРОБЛЕМА: Прямые вызовы зависимых действий
await send_welcome_email.kiq(user.email)  # Напрямую в регистрации

# РЕШЕНИЕ: Domain Events
@dataclass
class UserRegisteredEvent:
    user_id: int
    email: str
    username: str
    timestamp: datetime

class EventDispatcher:
    async def dispatch(self, event: DomainEvent):
        handlers = self._get_handlers(type(event))
        for handler in handlers:
            await handler.handle(event)

# Обработчики событий
class WelcomeEmailHandler:
    async def handle(self, event: UserRegisteredEvent):
        await send_welcome_email(event.email)

class UserAnalyticsHandler:
    async def handle(self, event: UserRegisteredEvent):
        await track_user_registration(event.user_id)
```

#### 4. Слабая типизация в некоторых местах

**Использование примитивных типов**
```python
# ПРОБЛЕМА: Строки вместо Value Objects
role: Mapped[str] = mapped_column(default="user")
kfa: Mapped[Literal["1", "2", "3", "4", "5"]] = mapped_column(nullable=True)

# РЕШЕНИЕ: Value Objects
@dataclass(frozen=True)
class UserRole:
    value: str

    def __post_init__(self):
        if self.value not in ['user', 'admin', 'moderator']:
            raise ValueError(f"Invalid role: {self.value}")

    @property
    def is_admin(self) -> bool:
        return self.value == 'admin'

@dataclass(frozen=True)
class KFALevel:
    level: int

    def __post_init__(self):
        if not 1 <= self.level <= 5:
            raise ValueError("KFA level must be between 1 and 5")

    @property
    def description(self) -> str:
        descriptions = {
            1: "Очень низкий",
            2: "Низкий",
            3: "Средний",
            4: "Высокий",
            5: "Очень высокий"
        }
        return descriptions[self.level]
```

#### 5. Отсутствие бизнес-правил для продуктов

**Нет валидации продуктов**
```python
# ПРОБЛЕМА: Простое добавление в очередь без проверок
@router.post("/pending")
async def add_pending_product(data: PendingProductCreate, session: AsyncSession):
    if await check_pending_exists(session, data.name):
        raise HTTPException(status_code=400, detail="Продукт уже в очереди")
    await create_pending_product(session, data.name)

# РЕШЕНИЕ: Бизнес-правила
class ProductBusinessRules:
    @staticmethod
    async def can_add_to_pending(product_name: str, session: AsyncSession) -> ValidationResult:
        errors = []

        # Проверка формата названия
        if len(product_name) < 3:
            errors.append("Название продукта должно содержать минимум 3 символа")

        # Проверка на запрещенные слова
        forbidden_words = ['тест', 'test', 'temp']
        if any(word in product_name.lower() for word in forbidden_words):
            errors.append("Название содержит запрещенные слова")

        # Проверка существования
        if await check_pending_exists(session, product_name):
            errors.append("Продукт уже в очереди на добавление")

        existing_product = await find_similar_product(session, product_name)
        if existing_product:
            errors.append(f"Похожий продукт уже существует: {existing_product.title}")

        return ValidationResult(is_valid=len(errors) == 0, errors=errors)
```

### 🔧 Рекомендуемые улучшения

#### 1. Создать доменные сервисы
```python
# domain/services/user_service.py
class UserService:
    def __init__(
        self,
        user_repo: UserRepository,
        email_service: EmailService,
        event_dispatcher: EventDispatcher
    ):
        self._user_repo = user_repo
        self._email_service = email_service
        self._event_dispatcher = event_dispatcher

    async def register_user(self, user_data: UserCreate) -> UserResponse:
        """Регистрация пользователя с полной бизнес-логикой"""

        # 1. Валидация бизнес-правил
        validation_result = await self._validate_registration(user_data)
        if not validation_result.is_valid:
            raise BusinessRuleViolationException(validation_result.errors)

        # 2. Создание пользователя
        user = await self._user_repo.create(user_data)

        # 3. Генерация события
        event = UserRegisteredEvent(
            user_id=user.id,
            email=user.email,
            username=user.username,
            timestamp=datetime.now(UTC)
        )

        # 4. Dispatch события
        await self._event_dispatcher.dispatch(event)

        return user

    async def _validate_registration(self, user_data: UserCreate) -> ValidationResult:
        """Валидация бизнес-правил регистрации"""
        errors = []

        # Проверка уникальности email
        if await self._user_repo.exists_by_email(user_data.email):
            errors.append("Пользователь с таким email уже существует")

        # Проверка уникальности username
        if await self._user_repo.exists_by_username(user_data.username):
            errors.append("Пользователь с таким именем уже существует")

        # Проверка сложности пароля
        password_errors = PasswordValidator.validate_strength(user_data.password)
        errors.extend(password_errors)

        return ValidationResult(is_valid=len(errors) == 0, errors=errors)

# domain/services/product_service.py
class ProductService:
    async def search_products(self, query: str, filters: ProductFilters) -> SearchResult:
        """Поиск продуктов с бизнес-логикой"""

        # 1. Валидация поискового запроса
        if len(query.strip()) < 2:
            raise InvalidSearchQueryException("Запрос должен содержать минимум 2 символа")

        # 2. Нормализация запроса
        normalized_query = self._normalize_search_query(query)

        # 3. Поиск продуктов
        products = await self._product_repo.search(normalized_query, filters)

        # 4. Ранжирование результатов
        ranked_products = self._rank_search_results(products, normalized_query)

        # 5. Применение бизнес-правил фильтрации
        filtered_products = self._apply_business_filters(ranked_products)

        return SearchResult(
            products=filtered_products,
            total_count=len(filtered_products),
            query=normalized_query
        )
```

#### 2. Добавить Value Objects
```python
# domain/value_objects.py
@dataclass(frozen=True)
class Email:
    value: str

    def __post_init__(self):
        if not self._is_valid_email(self.value):
            raise ValueError(f"Invalid email: {self.value}")

    @staticmethod
    def _is_valid_email(email: str) -> bool:
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None

@dataclass(frozen=True)
class Username:
    value: str

    def __post_init__(self):
        if not 3 <= len(self.value) <= 20:
            raise ValueError("Username must be between 3 and 20 characters")
        if not self.value.isalnum():
            raise ValueError("Username must contain only letters and numbers")

@dataclass(frozen=True)
class ProductName:
    value: str

    def __post_init__(self):
        if len(self.value.strip()) < 3:
            raise ValueError("Product name must be at least 3 characters")
        if len(self.value) > 100:
            raise ValueError("Product name must not exceed 100 characters")
```

#### 3. Реализовать агрегаты
```python
# domain/aggregates/user.py
class UserAggregate:
    def __init__(self, user_data: UserData):
        self._data = user_data
        self._events: list[DomainEvent] = []

    def update_profile(self, profile_data: UserProfile) -> None:
        """Обновление профиля с бизнес-правилами"""

        # Валидация изменений
        self._validate_profile_update(profile_data)

        # Применение изменений
        old_profile = self._data.profile
        self._data.profile = profile_data

        # Генерация события
        event = UserProfileUpdatedEvent(
            user_id=self._data.id,
            old_profile=old_profile,
            new_profile=profile_data
        )
        self._events.append(event)

    def change_subscription_status(self, is_subscribed: bool) -> None:
        """Изменение статуса подписки"""
        if self._data.is_subscribed == is_subscribed:
            return  # Нет изменений

        self._data.is_subscribed = is_subscribed

        event = UserSubscriptionChangedEvent(
            user_id=self._data.id,
            is_subscribed=is_subscribed
        )
        self._events.append(event)

    def get_uncommitted_events(self) -> list[DomainEvent]:
        return self._events.copy()

    def mark_events_as_committed(self) -> None:
        self._events.clear()
```

#### 4. Добавить спецификации
```python
# domain/specifications.py
class UserSpecifications:
    @staticmethod
    def is_adult(user: User) -> bool:
        return user.age >= 18

    @staticmethod
    def can_access_premium_features(user: User) -> bool:
        return user.is_subscribed and user.is_active

    @staticmethod
    def needs_profile_completion(user: User) -> bool:
        return any([
            user.age is None,
            user.weight is None,
            user.height is None,
            user.goal is None
        ])

class ProductSpecifications:
    @staticmethod
    def is_suitable_for_diet(product: Product, diet_type: str) -> bool:
        """Проверка подходит ли продукт для определенной диеты"""
        diet_rules = {
            'vegetarian': lambda p: 'мясо' not in p.title.lower(),
            'vegan': lambda p: all(
                keyword not in p.title.lower()
                for keyword in ['мясо', 'молоко', 'яйцо', 'сыр']
            ),
            'keto': lambda p: p.carbs.total < 10,  # Меньше 10г углеводов
        }

        rule = diet_rules.get(diet_type)
        return rule(product) if rule else True
```

#### 5. Создать бизнес-исключения
```python
# domain/exceptions.py
class BusinessRuleViolationException(Exception):
    def __init__(self, violations: list[str]):
        self.violations = violations
        message = "Business rule violations: " + "; ".join(violations)
        super().__init__(message)

class UserAlreadyExistsException(BusinessRuleViolationException):
    def __init__(self, field: str, value: str):
        super().__init__([f"User with {field} '{value}' already exists"])

class ProductNotAvailableException(Exception):
    def __init__(self, product_id: int):
        super().__init__(f"Product {product_id} is not available")

class InvalidSearchQueryException(Exception):
    def __init__(self, reason: str):
        super().__init__(f"Invalid search query: {reason}")

# Обработка бизнес-исключений
@app.exception_handler(BusinessRuleViolationException)
async def business_rule_violation_handler(request: Request, exc: BusinessRuleViolationException):
    return ORJSONResponse(
        status_code=422,
        content={
            "status": "error",
            "error": {
                "message": "Business rule violation",
                "violations": exc.violations
            }
        }
    )
```

### 📊 Анализ текущей бизнес-логики

#### Покрытие доменов
- ✅ **Пользователи**: Базовая логика реализована
- ⚠️ **Продукты**: Поиск реализован, но мало бизнес-правил
- ✅ **Аутентификация**: Хорошо реализована
- ❌ **Питание**: Бизнес-логика отсутствует
- ❌ **Рекомендации**: Не реализовано
- ❌ **Аналитика**: Не реализовано

#### Сложность бизнес-правил
- **Простые**: 80% (валидация полей)
- **Средние**: 15% (проверка уникальности)
- **Сложные**: 5% (составная валидация)

### 🎯 Приоритеты развития

#### Фаза 1 (2 недели)
- Создать доменные сервисы для User и Product
- Добавить Value Objects для основных типов
- Реализовать систему событий
- Добавить бизнес-исключения

#### Фаза 2 (3 недели)
- Создать агрегаты для сложных операций
- Добавить спецификации для бизнес-правил
- Реализовать калькулятор питательности
- Добавить систему рекомендаций

#### Фаза 3 (4 недели)
- Создать планы питания
- Добавить tracking потребления
- Реализовать аналитику и отчеты
- Добавить интеграции с внешними API

### 🔍 Недостающая бизнес-логика

#### 1. Калькулятор питательности
```python
class NutritionCalculator:
    async def calculate_daily_needs(self, user: User) -> DailyNutritionNeeds:
        """Расчет суточной потребности в питательных веществах"""

        # Базовый метаболизм по формуле Миффлина-Сан Жеора
        if user.gender == "male":
            bmr = 10 * user.weight + 6.25 * user.height - 5 * user.age + 5
        else:
            bmr = 10 * user.weight + 6.25 * user.height - 5 * user.age - 161

        # Коэффициент активности на основе KFA
        activity_multipliers = {
            "1": 1.2,   # Сидячий образ жизни
            "2": 1.375, # Легкая активность
            "3": 1.55,  # Умеренная активность
            "4": 1.725, # Высокая активность
            "5": 1.9    # Очень высокая активность
        }

        tdee = bmr * activity_multipliers.get(user.kfa, 1.2)

        # Корректировка на цель
        if user.goal == "Снижение веса":
            calories = tdee * 0.8  # Дефицит 20%
        elif user.goal == "Увеличение веса":
            calories = tdee * 1.15  # Профицит 15%
        else:
            calories = tdee

        return DailyNutritionNeeds(
            calories=calories,
            proteins=calories * 0.3 / 4,  # 30% от калорий
            fats=calories * 0.25 / 9,     # 25% от калорий
            carbs=calories * 0.45 / 4     # 45% от калорий
        )
```

#### 2. Система рекомендаций
```python
class ProductRecommendationService:
    async def get_recommendations(
        self,
        user: User,
        current_nutrition: ConsumedNutrition
    ) -> list[ProductRecommendation]:
        """Рекомендации продуктов на основе текущего потребления"""

        daily_needs = await self._nutrition_calculator.calculate_daily_needs(user)
        remaining_needs = daily_needs - current_nutrition

        recommendations = []

        # Если нужен белок
        if remaining_needs.proteins > 10:
            protein_products = await self._product_repo.find_high_protein()
            recommendations.extend(
                ProductRecommendation(product=p, reason="Для восполнения белка")
                for p in protein_products[:3]
            )

        # Если нужны витамины
        if self._is_vitamin_deficient(current_nutrition):
            vitamin_products = await self._product_repo.find_vitamin_rich()
            recommendations.extend(
                ProductRecommendation(product=p, reason="Для восполнения витаминов")
                for p in vitamin_products[:2]
            )

        return recommendations
```

**Итог**: Проект имеет хорошую техническую основу, но недостаточно развитую бизнес-логику. Основной фокус должен быть на создании доменных сервисов, добавлении сложных бизнес-правил и реализации core функциональности приложения для анализа питания.
