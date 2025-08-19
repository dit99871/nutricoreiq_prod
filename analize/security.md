# Анализ безопасности - NutriCoreIQ

## Общая оценка: 8/10

### ✅ Отличные решения безопасности

#### 1. Аутентификация и авторизация

**JWT Authentication**
```python
# Используются асимметричные ключи RSA
private_key_path: Path = BASE_DIR / "core" / "certs" / "jwt-private.pem"
public_key_path: Path = BASE_DIR / "core" / "certs" / "jwt-public.pem"

# Правильная структура токенов
ACCESS_TOKEN_TYPE = "access"
REFRESH_TOKEN_TYPE = "refresh"
```

**Безопасное хеширование паролей**
```python
# Использование bcrypt через passlib
from passlib.context import CryptContext
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
```

**Правильная проверка токенов**
```python
# Обработка всех типов JWT ошибок
except ExpiredSignatureError:
    # Истекший токен
except JWTError:
    # Невалидный токен
except FileNotFoundError:
    # Отсутствие ключей
```

#### 2. Защита от веб-атак

**CSRF Protection**
```python
# csrf_middleware.py - защита от CSRF
class CSRFMiddleware(BaseHTTPMiddleware):
    # Проверка CSRF токенов для POST/PUT/DELETE запросов
```

**Content Security Policy**
```python
# csp_middleware.py - защита от XSS
class CSPMiddleware(BaseHTTPMiddleware):
    # Генерация nonce для скриптов
    # Настройка CSP заголовков
```

**CORS конфигурация**
```python
# Правильная настройка CORS
allow_origins: list[str]        # Контролируемые домены
allow_credentials: bool         # Куки только с HTTPS
allow_methods: list[str]        # Ограниченные методы
allow_headers: list[str]        # Контролируемые заголовки
```

#### 3. Защита данных

**Валидация входных данных**
```python
# Pydantic схемы с ограничениями
username: Annotated[str, MinLen(3), MaxLen(20)]
password: Annotated[str, MinLen(8)]
email: EmailStr  # Автоматическая валидация email
```

**SQL Injection защита**
```python
# Использование ORM SQLAlchemy
stmt = select(User).filter(User.uid == uid)  # Параметризованные запросы
```

#### 4. Сессии и состояние

**Redis сессии**
```python
# Безопасное хранение сессий в Redis
class RedisSessionMiddleware:
    # Шифрование данных сессии
    # TTL для автоматического удаления
```

**Logout functionality**
```python
# Правильное аннулирование токенов
async def revoke_all_refresh_tokens(redis: Redis, user_uid: str):
    # Удаление всех refresh токенов пользователя
```

### ⚠️ Проблемы безопасности

#### 1. Критические уязвимости

**Хранение sensitive данных**
```python
# ПРОБЛЕМА: Возможность возврата хешированного пароля
class UserResponse(UserBase):
    hashed_password: bytes | None = None  # Не должно быть в response!

# ИСПРАВЛЕНИЕ:
class UserResponse(UserBase):
    # Убрать hashed_password полностью из response схем
```

**Слабая валидация пароля**
```python
# ПРОБЛЕМА: Только минимальная длина
password: Annotated[str, MinLen(8)]

# ИСПРАВЛЕНИЕ: Добавить сложность
@field_validator('password')
def validate_password(cls, v):
    if len(v) < 8:
        raise ValueError('Пароль должен быть не менее 8 символов')
    if not re.search(r'[A-Z]', v):
        raise ValueError('Пароль должен содержать заглавную букву')
    if not re.search(r'[a-z]', v):
        raise ValueError('Пароль должен содержать строчную букву')
    if not re.search(r'[0-9]', v):
        raise ValueError('Пароль должен содержать цифру')
    return v
```

#### 2. Недостающие механизмы безопасности

**Rate Limiting**
```python
# ОТСУТСТВУЕТ: Ограничение частоты запросов
# ДОБАВИТЬ:
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@router.post("/login")
@limiter.limit("5/minute")  # 5 попыток в минуту
async def login():
```

**Блокировка аккаунтов**
```python
# ОТСУТСТВУЕТ: Блокировка после неудачных попыток входа
# ДОБАВИТЬ в модель User:
failed_login_attempts: Mapped[int] = mapped_column(default=0)
locked_until: Mapped[datetime | None] = mapped_column(nullable=True)
```

**2FA (Two-Factor Authentication)**
```python
# ОТСУТСТВУЕТ: Двухфакторная аутентификация
# РЕКОМЕНДУЕТСЯ добавить:
totp_secret: Mapped[str | None] = mapped_column(nullable=True)
backup_codes: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
```

#### 3. Проблемы конфигурации

**Жестко заданные значения**
```python
# ПРОБЛЕМА: Время жизни токенов в коде
access_token_expires: int = 7  # 7 minutes - слишком коротко?
refresh_token_expires: int = 7  # 7 days

# ЛУЧШЕ: Настраиваемые значения из переменных окружения
```

**Отсутствие секретов в переменных окружения**
```python
# ПРОБЛЕМА: Нет проверки обязательных секретов
# ДОБАВИТЬ валидацию:
@field_validator('secret_key')
def validate_secret_key(cls, v):
    if len(v) < 32:
        raise ValueError('SECRET_KEY должен быть минимум 32 символа')
    return v
```

#### 4. Логирование безопасности

**Недостаточное логирование**
```python
# ОТСУТСТВУЕТ логирование:
- Неудачные попытки входа
- Смены паролей
- Подозрительная активность
- Admin действия

# ДОБАВИТЬ:
log.warning("Failed login attempt for user: %s from IP: %s", username, ip)
log.info("Password changed for user: %s", user.username)
```

### 🔧 Рекомендуемые улучшения

#### 1. Усилить аутентификацию
```python
# security/password_validator.py
class PasswordValidator:
    @staticmethod
    def validate_strength(password: str) -> tuple[bool, list[str]]:
        errors = []
        if len(password) < 12:
            errors.append("Минимум 12 символов")
        if not re.search(r'[A-Z]', password):
            errors.append("Заглавная буква")
        if not re.search(r'[a-z]', password):
            errors.append("Строчная буква")
        if not re.search(r'[0-9]', password):
            errors.append("Цифра")
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            errors.append("Специальный символ")

        return len(errors) == 0, errors

# Проверка на утекшие пароли через HaveIBeenPwned API
async def check_breached_password(password: str) -> bool:
    # Реализация проверки
```

#### 2. Добавить аудит безопасности
```python
# models/security_log.py
class SecurityEvent(IntIdPkMixin, Base):
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    event_type: Mapped[str] = mapped_column(index=True)  # login, logout, password_change
    ip_address: Mapped[str] = mapped_column(index=True)
    user_agent: Mapped[str | None] = mapped_column(nullable=True)
    success: Mapped[bool] = mapped_column(index=True)
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(default_factory=lambda: dt.datetime.now(dt.UTC))
```

#### 3. Добавить Rate Limiting
```python
# middleware/rate_limiter.py
class RateLimitMiddleware:
    def __init__(self, redis: Redis):
        self.redis = redis

    async def check_rate_limit(self, key: str, limit: int, window: int) -> bool:
        # Реализация sliding window rate limiting

# Применение к чувствительным endpoints
@limiter.limit("3/minute")  # Логин
@limiter.limit("1/minute")  # Смена пароля
@limiter.limit("10/minute") # API запросы
```

#### 4. Улучшить session security
```python
# Добавить в RedisSessionMiddleware
class SecureSessionMiddleware:
    def __init__(self):
        self.secure_flags = {
            'httponly': True,
            'secure': True,      # Только HTTPS
            'samesite': 'strict' # CSRF защита
        }

    async def rotate_session_id(self, request):
        # Смена session ID после логина
```

### 🛡️ Checklist безопасности

#### Аутентификация ✅/❌
- ✅ JWT с асимметричными ключами
- ✅ Bcrypt для паролей
- ✅ Refresh токены
- ❌ Сложность паролей
- ❌ Rate limiting на логин
- ❌ Account lockout
- ❌ 2FA

#### Авторизация ✅/❌
- ✅ Role-based (базовая)
- ❌ Permission-based
- ❌ Resource-level permissions
- ❌ Admin панель защита

#### Защита данных ✅/❌
- ✅ SQL injection защита (ORM)
- ✅ XSS защита (CSP)
- ✅ CSRF защита
- ✅ Input validation
- ❌ Output encoding
- ❌ Sensitive data masking

#### Инфраструктура ✅/❌
- ✅ HTTPS (в production)
- ✅ Secure headers
- ✅ CORS настройка
- ❌ Security headers (HSTS, etc.)
- ❌ Secrets management
- ❌ Vulnerability scanning

### 🎯 Приоритетные исправления

#### 1. Критический (немедленно)
- Убрать hashed_password из UserResponse
- Добавить валидацию сложности паролей
- Реализовать rate limiting для логина
- Добавить логирование security событий

#### 2. Высокий (1-2 недели)
- Добавить account lockout механизм
- Улучшить session security
- Добавить security headers middleware
- Реализовать аудит логирование

#### 3. Средний (1 месяц)
- Добавить 2FA
- Реализовать permission-based авторизацию
- Добавить проверку утекших паролей
- Настроить monitoring безопасности

### 📊 Метрики безопасности

#### Текущее состояние
- **Аутентификация**: 7/10
- **Авторизация**: 6/10
- **Защита данных**: 8/10
- **Мониторинг**: 4/10
- **Соответствие стандартам**: 6/10

#### Целевые показатели
- **OWASP Top 10 покрытие**: 80% ➔ 95%
- **Security headers**: 3/10 ➔ 8/10
- **Penetration testing**: Не проводилось ➔ Ежеквартально

### 🔒 Compliance требования

#### GDPR/Персональные данные
- ✅ Согласие на обработку (is_subscribed)
- ❌ Право на забвение (soft delete)
- ❌ Шифрование sensitive данных
- ❌ Data minimization принцип

#### Рекомендации для GDPR
```python
# Добавить soft delete
is_deleted: Mapped[bool] = mapped_column(default=False, index=True)
deleted_at: Mapped[datetime | None] = mapped_column(nullable=True)

# Шифрование PII данных
from cryptography.fernet import Fernet

class EncryptedType(TypeDecorator):
    impl = String

    def process_bind_param(self, value, dialect):
        if value is not None:
            return cipher_suite.encrypt(value.encode()).decode()
        return value
```

**Итог**: Проект имеет хорошую базовую безопасность, но требует усиления в области аутентификации, мониторинга и соответствия стандартам. Критические уязвимости должны быть исправлены немедленно.
