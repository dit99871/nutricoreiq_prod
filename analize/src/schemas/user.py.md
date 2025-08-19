# Анализ src/app/schemas/user.py

## Критические проблемы

### 1. Безопасность: Возможность утечки хешированного пароля (строка 21)
```python
# КРИТИЧЕСКАЯ ОШИБКА: hashed_password может попасть в response
class UserResponse(UserBase):
    id: int
    uid: str
    hashed_password: bytes | None = None  # НИКОГДА не должно быть в response!
```

**Исправление:**
```python
class UserResponse(UserBase):
    id: int
    uid: str
    # Полностью убрать hashed_password из response схем!
```

### 2. Неправильный синтаксис Literal (строка 30)
```python
# СИНТАКСИЧЕСКАЯ ОШИБКА: Неправильное использование Literal
goal: str = Literal["Снижение веса", "Увеличение веса", "Поддержание веса"] | None

# ИСПРАВЛЕНИЕ:
goal: Literal["Снижение веса", "Увеличение веса", "Поддержание веса"] | None = None
```

### 3. Неправильное объявление типа kfa в UserProfile (строка 39)
```python
# ОШИБКА: str с Literal constraint
kfa: str = Literal["1", "2", "3", "4", "5"]

# ИСПРАВЛЕНИЕ:
kfa: Literal["1", "2", "3", "4", "5"]
```

## Проблемы валидации

### 1. Слабая валидация пароля
```python
# ПРОБЛЕМА: Только минимальная длина
password: Annotated[str, MinLen(8)]

# УЛУЧШЕНИЕ: Сложная валидация пароля
from pydantic import field_validator
import re

class UserCreate(UserBase):
    password: Annotated[str, MinLen(8)]

    @field_validator('password')
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError('Пароль должен содержать минимум 8 символов')
        if len(v) > 128:
            raise ValueError('Пароль слишком длинный (максимум 128 символов)')
        if not re.search(r'[A-Z]', v):
            raise ValueError('Пароль должен содержать заглавную букву')
        if not re.search(r'[a-z]', v):
            raise ValueError('Пароль должен содержать строчную букву')
        if not re.search(r'[0-9]', v):
            raise ValueError('Пароль должен содержать цифру')
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError('Пароль должен содержать специальный символ')

        # Проверка на простые пароли
        common_passwords = ['password', '12345678', 'qwerty123']
        if v.lower() in common_passwords:
            raise ValueError('Пароль слишком простой')

        return v
```

### 2. Недостаточная валидация физических параметров
```python
# ПРОБЛЕМА: Только положительные числа
age: int = Field(gt=0)
weight: float = Field(gt=0)
height: float = Field(gt=0)

# УЛУЧШЕНИЕ: Реалистичные диапазоны
class UserProfile(BaseSchema):
    gender: Literal["female", "male"]
    age: int = Field(gt=15, le=120, description="Возраст от 16 до 120 лет")
    weight: float = Field(gt=20, le=500, description="Вес от 20 до 500 кг")
    height: float = Field(gt=50, le=250, description="Рост от 50 до 250 см")
    kfa: Literal["1", "2", "3", "4", "5"]
    goal: Literal["Снижение веса", "Увеличение веса", "Поддержание веса"]

    model_config = ConfigDict(strict=True)

    @field_validator('weight', 'height')
    @classmethod
    def validate_physical_params(cls, v: float, info) -> float:
        field_name = info.field_name

        if field_name == 'weight':
            if v < 30 or v > 300:
                raise ValueError('Вес должен быть в диапазоне 30-300 кг')
        elif field_name == 'height':
            if v < 100 or v > 230:
                raise ValueError('Рост должен быть в диапазоне 100-230 см')

        return v

    @model_validator(mode='after')
    def validate_bmi(self) -> 'UserProfile':
        """Валидация ИМТ на разумность"""
        if self.weight and self.height:
            bmi = self.weight / (self.height / 100) ** 2
            if bmi < 12 or bmi > 50:
                raise ValueError('Соотношение веса и роста выглядит нереалистично')
        return self
```

### 3. Отсутствие валидации username
```python
# УЛУЧШЕНИЕ: Валидация username
class UserBase(BaseSchema):
    username: Annotated[str, MinLen(3), MaxLen(20)]
    email: EmailStr
    is_subscribed: bool = True

    @field_validator('username')
    @classmethod
    def validate_username(cls, v: str) -> str:
        # Только буквы, цифры и _
        if not re.match(r'^[a-zA-Z0-9_]+$', v):
            raise ValueError('Username может содержать только буквы, цифры и знак подчеркивания')

        # Не может начинаться с цифры
        if v[0].isdigit():
            raise ValueError('Username не может начинаться с цифры')

        # Запрещенные имена
        forbidden_names = ['admin', 'root', 'user', 'test', 'api', 'www']
        if v.lower() in forbidden_names:
            raise ValueError('Это имя пользователя зарезервировано')

        return v
```

## Улучшения архитектуры

### 1. Разделить схемы по назначению
```python
# Отдельные схемы для разных операций
class UserCreateRequest(BaseSchema):
    """Схема для регистрации"""
    username: Annotated[str, MinLen(3), MaxLen(20)]
    email: EmailStr
    password: Annotated[str, MinLen(8)]

    # Валидаторы...

class UserPublicResponse(BaseSchema):
    """Публичная информация о пользователе"""
    id: int
    username: str

class UserPrivateResponse(UserPublicResponse):
    """Приватная информация для владельца аккаунта"""
    email: EmailStr
    is_subscribed: bool
    created_at: datetime

class UserAdminResponse(UserPrivateResponse):
    """Информация для администраторов"""
    uid: str
    is_active: bool
    role: str
    last_login: datetime | None
```

### 2. Добавить схемы для операций
```python
class PasswordChangeRequest(BaseSchema):
    current_password: Annotated[str, MinLen(8)]
    new_password: Annotated[str, MinLen(8)]

    @field_validator('new_password')
    @classmethod
    def validate_new_password(cls, v: str, info) -> str:
        # Применить валидацию сложности пароля
        return UserCreate.validate_password_strength(v)

    @model_validator(mode='after')
    def passwords_different(self) -> 'PasswordChangeRequest':
        if self.current_password == self.new_password:
            raise ValueError('Новый пароль должен отличаться от текущего')
        return self

class UserSearchFilters(BaseSchema):
    """Фильтры для поиска пользователей"""
    role: UserRole | None = None
    is_active: bool | None = None
    created_after: datetime | None = None
    created_before: datetime | None = None

class BulkUserOperation(BaseSchema):
    """Массовые операции с пользователями"""
    user_ids: list[int] = Field(min_items=1, max_items=100)
    operation: Literal["activate", "deactivate", "delete"]
    reason: str | None = None
```

## Полное исправленное решение

```python
from annotated_types import MinLen, MaxLen
from pydantic import ConfigDict, EmailStr, Field, field_validator, model_validator
from typing import Annotated, Literal
from datetime import datetime
import re

from .base import BaseSchema


class UserBase(BaseSchema):
    username: Annotated[str, MinLen(3), MaxLen(20)]
    email: EmailStr
    is_subscribed: bool = True

    @field_validator('username')
    @classmethod
    def validate_username(cls, v: str) -> str:
        if not re.match(r'^[a-zA-Z0-9_]+$', v):
            raise ValueError('Username может содержать только буквы, цифры и знак подчеркивания')

        if v[0].isdigit():
            raise ValueError('Username не может начинаться с цифры')

        forbidden_names = ['admin', 'root', 'user', 'test', 'api', 'www', 'support']
        if v.lower() in forbidden_names:
            raise ValueError('Это имя пользователя зарезервировано')

        return v


class UserCreate(UserBase):
    password: Annotated[str, MinLen(8)]

    @field_validator('password')
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError('Пароль должен содержать минимум 8 символов')
        if len(v) > 128:
            raise ValueError('Пароль слишком длинный')
        if not re.search(r'[A-Z]', v):
            raise ValueError('Пароль должен содержать заглавную букву')
        if not re.search(r'[a-z]', v):
            raise ValueError('Пароль должен содержать строчную букву')
        if not re.search(r'[0-9]', v):
            raise ValueError('Пароль должен содержать цифру')
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError('Пароль должен содержать специальный символ')

        common_passwords = ['password', '12345678', 'qwerty123', 'password123']
        if v.lower() in common_passwords:
            raise ValueError('Пароль слишком простой')

        return v


class UserResponse(UserBase):
    """Безопасная схема ответа без sensitive данных"""
    id: int
    uid: str
    # hashed_password полностью убран!


class UserAccount(UserBase):
    gender: Literal["female", "male"] | None = None
    age: int | None = None
    weight: float | None = None
    height: float | None = None
    kfa: str | None = None
    goal: Literal["Снижение веса", "Увеличение веса", "Поддержание веса"] | None = None
    created_at: datetime


class UserProfile(BaseSchema):
    gender: Literal["female", "male"]
    age: int = Field(gt=15, le=120)
    weight: float = Field(gt=20, le=500)
    height: float = Field(gt=50, le=250)
    kfa: Literal["1", "2", "3", "4", "5"]
    goal: Literal["Снижение веса", "Увеличение веса", "Поддержание веса"]

    model_config = ConfigDict(strict=True)

    @field_validator('weight', 'height')
    @classmethod
    def validate_physical_params(cls, v: float, info) -> float:
        field_name = info.field_name

        if field_name == 'weight' and (v < 30 or v > 300):
            raise ValueError('Вес должен быть в диапазоне 30-300 кг')
        elif field_name == 'height' and (v < 100 or v > 230):
            raise ValueError('Рост должен быть в диапазоне 100-230 см')

        return v

    @model_validator(mode='after')
    def validate_bmi(self) -> 'UserProfile':
        if self.weight and self.height:
            bmi = self.weight / (self.height / 100) ** 2
            if bmi < 12 or bmi > 50:
                raise ValueError('Соотношение веса и роста выглядит нереалистично')
        return self


class PasswordChange(BaseSchema):
    current_password: Annotated[str, MinLen(8)]
    new_password: Annotated[str, MinLen(8)]

    @field_validator('new_password')
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        return UserCreate.validate_password_strength(v)

    @model_validator(mode='after')
    def passwords_different(self) -> 'PasswordChange':
        if self.current_password == self.new_password:
            raise ValueError('Новый пароль должен отличаться от текущего')
        return self
```

## Приоритет исправлений

1. **КРИТИЧЕСКИЙ**: Убрать hashed_password из UserResponse схемы
2. **Критический**: Исправить синтаксические ошибки с Literal
3. **Высокий**: Добавить валидацию сложности пароля
4. **Средний**: Улучшить валидацию физических параметров
5. **Низкий**: Разделить схемы по назначению
