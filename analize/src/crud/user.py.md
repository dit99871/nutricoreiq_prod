# Анализ src/app/crud/user.py

## Проблемы возвращаемых типов

### 1. Неправильный возвращаемый тип в create_user (строка 148-181)
```python
# ПРОБЛЕМА: Возвращает UserCreate вместо созданного пользователя
async def create_user(
    session: AsyncSession,
    user_in: UserCreate,
) -> UserCreate | None:  # <- Неправильный тип!
    # ...
    return user_in  # <- Возвращает входные данные вместо созданного пользователя
```

**Исправление:**
```python
async def create_user(
    session: AsyncSession,
    user_in: UserCreate,
) -> UserResponse:  # Правильный возвращаемый тип
    try:
        hashed_password = get_password_hash(user_in.password)
        db_user = User(
            **user_in.model_dump(exclude={"password"}),
            hashed_password=hashed_password,
        )
        session.add(db_user)
        await session.commit()
        await session.refresh(db_user)

        # Возвращаем созданного пользователя, а не входные данные
        return UserResponse.model_validate(db_user)

    except SQLAlchemyError as e:
        await session.rollback()
        log.error("Database error creating user with email %s: %s", user_in.email, str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": "Ошибка при создании пользователя"},
        )
```

### 2. Проблемы с обработкой ошибок
```python
# ПРОБЛЕМА: Неконсистентная обработка ошибок
except SQLAlchemyError as e:
    log.error("Database error creating user_in with email %s: %s", user_in.email, str(e))
    await session.rollback()
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail={"message": "Ошибка при создании пользователя"},
    )

# УЛУЧШЕНИЕ: Более детальная обработка ошибок
except IntegrityError as e:
    await session.rollback()

    # Определяем тип нарушения ограничения
    if "email" in str(e.orig).lower():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "Пользователь с таким email уже существует"}
        )
    elif "username" in str(e.orig).lower():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "Пользователь с таким именем уже существует"}
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "Нарушение ограничений базы данных"}
        )

except SQLAlchemyError as e:
    await session.rollback()
    log.error("Database error creating user with email %s: %s", user_in.email, str(e))
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail={"message": "Внутренняя ошибка базы данных"}
    )
```

## Проблемы производительности

### 1. Отсутствие оптимизации запросов
```python
# ПРОБЛЕМА: Неэффективные запросы в _get_user_by_filter
stmt = select(User).filter(filter_condition, User.is_active == True)

# УЛУЧШЕНИЕ: Добавить select-only для нужных полей
def _build_user_select(include_sensitive: bool = False):
    """Строит SELECT с нужными полями"""
    if include_sensitive:
        return select(User)
    else:
        # Исключаем sensitive поля для обычных запросов
        return select(
            User.id,
            User.uid,
            User.username,
            User.email,
            User.is_active,
            User.is_subscribed,
            User.role,
            User.created_at
        )

# Использование:
stmt = _build_user_select().filter(filter_condition, User.is_active == True)
```

### 2. Отсутствие пагинации для списочных запросов
```python
# ДОБАВИТЬ: Функции для получения списков пользователей с пагинацией
async def get_users_paginated(
    session: AsyncSession,
    offset: int = 0,
    limit: int = 20,
    filters: dict = None
) -> tuple[list[UserResponse], int]:
    """Получение списка пользователей с пагинацией"""

    base_query = select(User).where(User.is_active == True)

    # Применение фильтров
    if filters:
        if role := filters.get('role'):
            base_query = base_query.where(User.role == role)
        if created_after := filters.get('created_after'):
            base_query = base_query.where(User.created_at >= created_after)

    # Подсчет общего количества
    count_query = select(func.count()).select_from(base_query.subquery())
    total_result = await session.execute(count_query)
    total_count = total_result.scalar()

    # Получение страницы данных
    paginated_query = base_query.offset(offset).limit(limit).order_by(User.created_at.desc())
    result = await session.execute(paginated_query)
    users = result.scalars().all()

    return [UserResponse.model_validate(user) for user in users], total_count
```

## Отсутствующая функциональность

### 1. Обновление пользователя
```python
# ДОБАВИТЬ: Функция обновления пользователя
async def update_user(
    session: AsyncSession,
    user_id: int,
    user_update: UserUpdate
) -> UserResponse:
    """Обновление данных пользователя"""

    stmt = select(User).where(User.id == user_id, User.is_active == True)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": "Пользователь не найден"}
        )

    # Обновление полей
    update_data = user_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)

    # Обновление timestamp
    user.updated_at = dt.datetime.now(dt.UTC)

    try:
        await session.commit()
        await session.refresh(user)
        return UserResponse.model_validate(user)
    except SQLAlchemyError as e:
        await session.rollback()
        log.error("Error updating user %d: %s", user_id, str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": "Ошибка при обновлении пользователя"}
        )
```

### 2. Soft delete
```python
# ДОБАВИТЬ: Мягкое удаление пользователя
async def soft_delete_user(
    session: AsyncSession,
    user_id: int,
    deleted_by: int
) -> bool:
    """Мягкое удаление пользователя"""

    stmt = select(User).where(User.id == user_id, User.is_active == True)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": "Пользователь не найден"}
        )

    # Деактивация вместо удаления
    user.is_active = False
    user.deleted_at = dt.datetime.now(dt.UTC)
    user.deleted_by = deleted_by

    try:
        await session.commit()
        log.info("User %d soft deleted by user %d", user_id, deleted_by)
        return True
    except SQLAlchemyError as e:
        await session.rollback()
        log.error("Error soft deleting user %d: %s", user_id, str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": "Ошибка при удалении пользователя"}
        )
```

### 3. Поиск пользователей
```python
# ДОБАВИТЬ: Поиск пользователей
async def search_users(
    session: AsyncSession,
    search_query: str,
    limit: int = 10
) -> list[UserResponse]:
    """Поиск пользователей по имени или email"""

    search_pattern = f"%{search_query.lower()}%"

    stmt = (
        select(User)
        .where(
            User.is_active == True,
            or_(
                func.lower(User.username).like(search_pattern),
                func.lower(User.email).like(search_pattern)
            )
        )
        .limit(limit)
        .order_by(User.username)
    )

    result = await session.execute(stmt)
    users = result.scalars().all()

    return [UserResponse.model_validate(user) for user in users]
```

## Улучшения безопасности

### 1. Проверка прав доступа
```python
# ДОБАВИТЬ: Проверка прав доступа
async def check_user_access(
    session: AsyncSession,
    requesting_user_id: int,
    target_user_id: int,
    required_permission: str = "read"
) -> bool:
    """Проверка прав доступа к пользователю"""

    # Пользователь может читать свои данные
    if requesting_user_id == target_user_id:
        return True

    # Получаем роль запрашивающего пользователя
    stmt = select(User.role).where(User.id == requesting_user_id)
    result = await session.execute(stmt)
    role = result.scalar_one_or_none()

    if not role:
        return False

    # Права доступа по ролям
    permissions = {
        "admin": ["read", "write", "delete"],
        "moderator": ["read", "write"],
        "user": []
    }

    return required_permission in permissions.get(role, [])
```

### 2. Аудит логирование
```python
# ДОБАВИТЬ: Аудит операций
async def log_user_operation(
    session: AsyncSession,
    operation: str,
    target_user_id: int,
    performed_by: int,
    details: dict = None
):
    """Логирование операций с пользователями для аудита"""

    audit_log = UserAuditLog(
        operation=operation,
        target_user_id=target_user_id,
        performed_by=performed_by,
        details=details or {},
        timestamp=dt.datetime.now(dt.UTC),
        ip_address=request.client.host if hasattr(request, 'client') else None
    )

    session.add(audit_log)
    await session.commit()
```

## Полное исправленное решение

```python
# src/app/crud/user.py - улучшенная версия
import datetime as dt
from datetime import datetime
from typing import Optional, Tuple, List

from fastapi import status, HTTPException
from pydantic import EmailStr
from sqlalchemy import func, or_, select, and_
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.core.logger import get_logger
from src.app.models import User
from src.app.schemas.user import UserCreate, UserResponse, UserUpdate
from src.app.core.utils.auth import get_password_hash

log = get_logger("user_crud")


class UserCRUD:
    """CRUD операции для пользователей"""

    @staticmethod
    async def create_user(
        session: AsyncSession,
        user_in: UserCreate,
    ) -> UserResponse:
        """Создание нового пользователя"""
        try:
            hashed_password = get_password_hash(user_in.password)
            db_user = User(
                **user_in.model_dump(exclude={"password"}),
                hashed_password=hashed_password,
            )
            session.add(db_user)
            await session.commit()
            await session.refresh(db_user)

            log.info("User created successfully: %s", user_in.email)
            return UserResponse.model_validate(db_user)

        except IntegrityError as e:
            await session.rollback()

            error_msg = str(e.orig).lower()
            if "email" in error_msg:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={"message": "Пользователь с таким email уже существует"}
                )
            elif "username" in error_msg:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={"message": "Пользователь с таким именем уже существует"}
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={"message": "Нарушение ограничений базы данных"}
                )

        except SQLAlchemyError as e:
            await session.rollback()
            log.error("Database error creating user with email %s: %s", user_in.email, str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"message": "Внутренняя ошибка базы данных"}
            )

    @staticmethod
    async def get_user_by_id(
        session: AsyncSession,
        user_id: int,
        include_inactive: bool = False
    ) -> Optional[UserResponse]:
        """Получение пользователя по ID"""
        conditions = [User.id == user_id]
        if not include_inactive:
            conditions.append(User.is_active == True)

        stmt = select(User).where(and_(*conditions))
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        return UserResponse.model_validate(user) if user else None

    @staticmethod
    async def get_users_paginated(
        session: AsyncSession,
        offset: int = 0,
        limit: int = 20,
        filters: Optional[dict] = None
    ) -> Tuple[List[UserResponse], int]:
        """Получение списка пользователей с пагинацией"""

        base_query = select(User).where(User.is_active == True)

        # Применение фильтров
        if filters:
            if role := filters.get('role'):
                base_query = base_query.where(User.role == role)
            if created_after := filters.get('created_after'):
                base_query = base_query.where(User.created_at >= created_after)

        # Подсчет общего количества
        count_stmt = select(func.count()).select_from(base_query.subquery())
        total_result = await session.execute(count_stmt)
        total_count = total_result.scalar()

        # Получение страницы данных
        paginated_stmt = (
            base_query
            .offset(offset)
            .limit(limit)
            .order_by(User.created_at.desc())
        )
        result = await session.execute(paginated_stmt)
        users = result.scalars().all()

        return [UserResponse.model_validate(user) for user in users], total_count

    @staticmethod
    async def update_user(
        session: AsyncSession,
        user_id: int,
        user_update: UserUpdate
    ) -> UserResponse:
        """Обновление данных пользователя"""

        stmt = select(User).where(User.id == user_id, User.is_active == True)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"message": "Пользователь не найден"}
            )

        # Обновление полей
        update_data = user_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(user, field, value)

        # Обновление timestamp
        user.updated_at = dt.datetime.now(dt.UTC)

        try:
            await session.commit()
            await session.refresh(user)
            log.info("User %d updated successfully", user_id)
            return UserResponse.model_validate(user)
        except SQLAlchemyError as e:
            await session.rollback()
            log.error("Error updating user %d: %s", user_id, str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"message": "Ошибка при обновлении пользователя"}
            )


# Переиспользуем существующие функции как методы класса
create_user = UserCRUD.create_user
get_user_by_id = UserCRUD.get_user_by_id
get_users_paginated = UserCRUD.get_users_paginated
update_user = UserCRUD.update_user

# Сохраняем существующие функции для обратной совместимости
async def get_user_by_email(session: AsyncSession, email: EmailStr) -> Optional[UserResponse]:
    """Получение пользователя по email (обратная совместимость)"""
    stmt = select(User).where(User.email == email, User.is_active == True)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()
    return UserResponse.model_validate(user) if user else None

async def get_user_by_uid(session: AsyncSession, uid: str) -> UserResponse:
    """Получение пользователя по UID (обратная совместимость)"""
    stmt = select(User).where(User.uid == uid, User.is_active == True)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": "Пользователь не найден"}
        )

    return UserResponse.model_validate(user)
```

## Приоритет исправлений

1. **Критический**: Исправить возвращаемый тип в create_user
2. **Высокий**: Улучшить обработку ошибок (IntegrityError)
3. **Средний**: Добавить функции обновления и поиска
4. **Низкий**: Добавить пагинацию и аудит логирование
