# Анализ src/app/routers/auth.py

## Проблемы безопасности

### 1. Отсутствие rate limiting (строки 40-80)
```python
# ПРОБЛЕМА: Нет ограничения частоты попыток регистрации и входа
@router.post("/register")
async def register_user(...)
    # Может быть использовано для спама/атак

@router.post("/login")
async def login(...)
    # Может быть использовано для brute force атак
```

**Исправление:**
```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)

@router.post("/register")
@limiter.limit("3/minute")  # 3 регистрации в минуту с IP
async def register_user(
    request: Request,
    user_in: UserCreate,
    session: Annotated[AsyncSession, Depends(db_helper.session_getter)],
):
    # Дополнительная проверка по email
    if await check_recent_registrations(session, user_in.email):
        raise HTTPException(
            status_code=429,
            detail={"message": "Слишком много попыток регистрации. Попробуйте позже."}
        )

@router.post("/login")
@limiter.limit("5/minute")  # 5 попыток входа в минуту
async def login(
    request: Request,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: Annotated[AsyncSession, Depends(db_helper.session_getter)],
):
    # ...
```

### 2. Отсутствие логирования security событий
```python
# ПРОБЛЕМА: Недостаточное логирование для мониторинга атак
# Нужно логировать:
- Неудачные попытки входа
- Подозрительную активность
- Смены паролей
- Блокировки аккаунтов

# ДОБАВИТЬ:
async def log_security_event(
    event_type: str,
    user_identifier: str,
    request: Request,
    success: bool,
    details: dict = None
):
    """Логирование событий безопасности"""
    log.info(
        "Security event: %s | User: %s | IP: %s | Success: %s | Details: %s",
        event_type,
        user_identifier,
        request.client.host if request.client else "unknown",
        success,
        details or {}
    )

# В функциях:
await log_security_event("login_attempt", form_data.username, request, True)
await log_security_event("registration", user_in.email, request, True)
```

### 3. Отсутствие проверки силы пароля
```python
# ПРОБЛЕМА: Проверка пароля только в схеме, но не при смене
# ДОБАВИТЬ в password change:
@router.post("/change-password")
async def change_password(
    password_data: PasswordChange,
    session: Annotated[AsyncSession, Depends(db_helper.session_getter)],
    current_user: Annotated[UserResponse, Depends(get_current_auth_user)],
):
    # Проверить силу нового пароля
    if not is_password_strong(password_data.new_password):
        raise HTTPException(
            status_code=400,
            detail={"message": "Пароль не соответствует требованиям безопасности"}
        )
```

## Проблемы архитектуры

### 1. Смешивание ответственности (строки 61-80)
```python
# ПРОБЛЕМА: Вся логика регистрации в одной функции
async def register_user(...):
    # Проверка существования пользователя
    db_user = await get_user_by_email(session, user_in.email)
    if db_user:
        raise HTTPException(...)

    # Создание пользователя
    user = await create_user(session, user_in)

    # Отправка email
    await send_welcome_email.kiq(user.email)

# РЕШЕНИЕ: Вынести в сервисный слой
class AuthService:
    async def register_user(self, user_data: UserCreate, request: Request) -> UserResponse:
        # Валидация бизнес-правил
        await self._validate_registration(user_data, request)

        # Создание пользователя
        user = await self._user_repo.create(user_data)

        # Генерация событий
        await self._event_dispatcher.dispatch(UserRegisteredEvent(user.id, user.email))

        return user
```

### 2. Отсутствие валидации бизнес-правил
```python
# ПРОБЛЕМА: Только проверка существования email
# ДОБАВИТЬ валидацию:
class RegistrationValidator:
    @staticmethod
    async def validate_registration(
        user_data: UserCreate,
        session: AsyncSession,
        request: Request
    ) -> list[str]:
        errors = []

        # Проверка email
        if await get_user_by_email(session, user_data.email):
            errors.append("Пользователь с таким email уже существует")

        # Проверка username
        if await get_user_by_username(session, user_data.username):
            errors.append("Пользователь с таким именем уже существует")

        # Проверка на временные email
        if is_disposable_email(user_data.email):
            errors.append("Временные email адреса не разрешены")

        # Проверка на слишком частые регистрации с IP
        if await check_ip_registration_rate(session, request.client.host):
            errors.append("Слишком много регистраций с этого IP")

        return errors
```

## Отсутствующая функциональность

### 1. Подтверждение email
```python
# ДОБАВИТЬ: Email verification
@router.post("/verify-email")
async def verify_email(
    token: str,
    session: Annotated[AsyncSession, Depends(db_helper.session_getter)],
):
    """Подтверждение email адреса"""
    try:
        # Декодировать токен
        payload = decode_verification_token(token)
        user_id = payload.get("user_id")

        # Активировать пользователя
        await activate_user(session, user_id)

        return {"message": "Email успешно подтвержден"}
    except InvalidTokenException:
        raise HTTPException(
            status_code=400,
            detail={"message": "Недействительный или истекший токен"}
        )

@router.post("/resend-verification")
async def resend_verification_email(
    email: EmailStr,
    session: Annotated[AsyncSession, Depends(db_helper.session_getter)],
):
    """Повторная отправка письма подтверждения"""
    user = await get_user_by_email(session, email)
    if not user:
        # Не показываем существование email по соображениям безопасности
        return {"message": "Если email существует, письмо будет отправлено"}

    if user.is_verified:
        return {"message": "Email уже подтвержден"}

    await send_verification_email.kiq(user.email)
    return {"message": "Письмо подтверждения отправлено"}
```

### 2. Восстановление пароля
```python
# ДОБАВИТЬ: Password reset
@router.post("/forgot-password")
async def forgot_password(
    email: EmailStr,
    session: Annotated[AsyncSession, Depends(db_helper.session_getter)],
):
    """Запрос на восстановление пароля"""
    user = await get_user_by_email(session, email)
    if user:
        # Создать токен восстановления
        reset_token = generate_password_reset_token(user.id)

        # Сохранить в Redis с TTL
        await save_reset_token(user.id, reset_token)

        # Отправить email
        await send_password_reset_email.kiq(user.email, reset_token)

    # Всегда возвращаем одинаковый ответ по соображениям безопасности
    return {"message": "Если email существует, инструкции будут отправлены"}

@router.post("/reset-password")
async def reset_password(
    token: str,
    new_password: str,
    session: Annotated[AsyncSession, Depends(db_helper.session_getter)],
):
    """Сброс пароля по токену"""
    # Валидировать токен
    user_id = await validate_reset_token(token)
    if not user_id:
        raise HTTPException(
            status_code=400,
            detail={"message": "Недействительный или истекший токен"}
        )

    # Обновить пароль
    await update_user_password(session, user_id, new_password)

    # Аннулировать все сессии пользователя
    await revoke_all_user_sessions(user_id)

    return {"message": "Пароль успешно изменен"}
```

### 3. Двухфакторная аутентификация
```python
# ДОБАВИТЬ: 2FA endpoints
@router.post("/enable-2fa")
async def enable_2fa(
    current_user: Annotated[UserResponse, Depends(get_current_auth_user)],
    session: Annotated[AsyncSession, Depends(db_helper.session_getter)],
):
    """Включение двухфакторной аутентификации"""
    if current_user.totp_enabled:
        raise HTTPException(400, detail={"message": "2FA уже включена"})

    # Генерировать TOTP секрет
    secret = generate_totp_secret()
    qr_code = generate_qr_code(current_user.email, secret)

    # Временно сохранить секрет
    await save_temp_totp_secret(current_user.id, secret)

    return {
        "secret": secret,
        "qr_code": qr_code,
        "backup_codes": generate_backup_codes()
    }

@router.post("/verify-2fa")
async def verify_2fa(
    totp_code: str,
    current_user: Annotated[UserResponse, Depends(get_current_auth_user)],
    session: Annotated[AsyncSession, Depends(db_helper.session_getter)],
):
    """Подтверждение настройки 2FA"""
    temp_secret = await get_temp_totp_secret(current_user.id)
    if not temp_secret:
        raise HTTPException(400, detail={"message": "Настройка 2FA не найдена"})

    if not verify_totp_code(temp_secret, totp_code):
        raise HTTPException(400, detail={"message": "Неверный код"})

    # Включить 2FA для пользователя
    await enable_user_2fa(session, current_user.id, temp_secret)

    return {"message": "2FA успешно включена"}
```

## Полное исправленное решение

```python
# src/app/routers/auth.py - улучшенная версия
from typing import Annotated
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import ORJSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from slowapi import Limiter
from slowapi.util import get_remote_address
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.core.exceptions import ExpiredTokenException
from src.app.core import db_helper
from src.app.core.logger import get_logger
from src.app.core.redis import get_redis
from src.app.services.auth_service import AuthService
from src.app.schemas.user import (
    PasswordChange, UserCreate, UserResponse,
    EmailVerificationRequest, PasswordResetRequest
)

log = get_logger("auth_router")
limiter = Limiter(key_func=get_remote_address)

router = APIRouter(
    tags=["Authentication"],
    default_response_class=ORJSONResponse,
)

# Инициализация сервиса
auth_service = AuthService()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("3/minute")
async def register_user(
    request: Request,
    user_in: UserCreate,
    session: Annotated[AsyncSession, Depends(db_helper.session_getter)],
) -> UserResponse:
    """Регистрация нового пользователя с валидацией и rate limiting"""

    try:
        user = await auth_service.register_user(user_in, request, session)

        await log_security_event(
            "user_registration",
            user_in.email,
            request,
            True,
            {"user_id": user.id}
        )

        return user

    except Exception as e:
        await log_security_event(
            "user_registration",
            user_in.email,
            request,
            False,
            {"error": str(e)}
        )
        raise


@router.post("/login", response_model=UserResponse)
@limiter.limit("5/minute")
async def login(
    request: Request,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: Annotated[AsyncSession, Depends(db_helper.session_getter)],
) -> UserResponse:
    """Аутентификация пользователя с rate limiting и логированием"""

    try:
        user_response = await auth_service.authenticate_user(
            form_data.username,
            form_data.password,
            request,
            session
        )

        await log_security_event(
            "user_login",
            form_data.username,
            request,
            True,
            {"user_id": user_response.id}
        )

        return user_response

    except HTTPException as e:
        await log_security_event(
            "user_login",
            form_data.username,
            request,
            False,
            {"error": e.detail}
        )

        # Увеличить счетчик неудачных попыток
        await track_failed_login(session, form_data.username, request.client.host)
        raise


@router.post("/verify-email")
async def verify_email(
    verification_data: EmailVerificationRequest,
    session: Annotated[AsyncSession, Depends(db_helper.session_getter)],
):
    """Подтверждение email адреса"""
    return await auth_service.verify_email(verification_data.token, session)


@router.post("/forgot-password")
@limiter.limit("2/minute")
async def forgot_password(
    request: Request,
    reset_data: PasswordResetRequest,
    session: Annotated[AsyncSession, Depends(db_helper.session_getter)],
):
    """Запрос на восстановление пароля"""
    return await auth_service.initiate_password_reset(
        reset_data.email,
        request,
        session
    )


@router.post("/logout")
async def logout(
    request: Request,
    current_user: Annotated[UserResponse, Depends(get_current_auth_user)],
    redis: Redis = Depends(get_redis),
):
    """Выход из системы с аннулированием токенов"""

    try:
        await auth_service.logout_user(current_user, request, redis)

        await log_security_event(
            "user_logout",
            current_user.email,
            request,
            True,
            {"user_id": current_user.id}
        )

        return {"message": "Успешный выход из системы"}

    except Exception as e:
        await log_security_event(
            "user_logout",
            current_user.email,
            request,
            False,
            {"error": str(e)}
        )
        raise


async def log_security_event(
    event_type: str,
    user_identifier: str,
    request: Request,
    success: bool,
    details: dict = None
):
    """Логирование событий безопасности для мониторинга"""

    log_data = {
        "event_type": event_type,
        "user_identifier": user_identifier,
        "ip_address": request.client.host if request.client else "unknown",
        "user_agent": request.headers.get("user-agent", "unknown"),
        "success": success,
        "timestamp": datetime.now().isoformat(),
        "details": details or {}
    }

    if success:
        log.info("Security event: %(event_type)s succeeded", log_data, extra=log_data)
    else:
        log.warning("Security event: %(event_type)s failed", log_data, extra=log_data)


async def track_failed_login(session: AsyncSession, username: str, ip_address: str):
    """Отслеживание неудачных попыток входа для блокировки"""

    # Логика блокировки аккаунта после N неудачных попыток
    # Реализация зависит от требований безопасности
    pass
```

## Приоритет исправлений

1. **Критический**: Добавить rate limiting для login/register
2. **Высокий**: Добавить логирование security событий
3. **Высокий**: Вынести бизнес-логику в сервисный слой
4. **Средний**: Добавить email verification
5. **Средний**: Добавить password reset
6. **Низкий**: Добавить 2FA поддержку
