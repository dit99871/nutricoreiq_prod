import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

import src.app.core.utils.validators
from src.app.core.exceptions import DatabaseError, NotFoundError
from src.app.core.models import User
from src.app.core.repo.user import (
    choose_subscribe_status,
    create_user,
    get_user_by_email,
    get_user_by_name,
    get_user_by_uid,
)
from src.app.core.schemas.user import UserCreate, UserPublic
from src.app.core.services.cache import CacheService


def mock_validate_password_strength(v):
    if hasattr(v, "get_secret_value"):
        v = v.get_secret_value()
    if not isinstance(v, str):
        raise ValueError("Password must be a string")
    return v


src.app.core.utils.validators.validate_password_strength = (
    mock_validate_password_strength
)


@pytest.fixture
def mock_user():
    return User(
        id=1,
        uid=str(uuid.uuid4()),
        username="test_user",
        email="test@example.com",
        hashed_password=b"hashed_password",
        is_active=True,
        is_subscribed=True,
    )


@pytest.fixture
def user_create_data():
    return {
        "username": "new_user",
        "email": "newuser@example.com",
        "password": "StrongPass123!",
    }


@pytest.mark.asyncio
async def test_get_user_by_uid_cache_hit(mock_user):
    mock_session = AsyncMock(spec=AsyncSession)
    mock_cache_data = {
        "id": mock_user.id,
        "uid": mock_user.uid,
        "username": mock_user.username,
        "email": mock_user.email,
    }

    with patch.object(
        CacheService, "get_user", new_callable=AsyncMock
    ) as mock_get_cache:
        mock_get_cache.return_value = mock_cache_data
        result = await get_user_by_uid(mock_session, mock_user.uid)

        assert result.id == mock_user.id
        assert result.username == mock_user.username
        mock_session.execute.assert_not_called()


@pytest.mark.asyncio
async def test_get_user_by_uid_db_success(mock_user):
    mock_session = AsyncMock(spec=AsyncSession)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_user
    mock_session.execute.return_value = mock_result

    with (
        patch.object(
            CacheService, "get_user", new_callable=AsyncMock
        ) as mock_get_cache,
        patch.object(
            CacheService, "set_user", new_callable=AsyncMock
        ) as mock_set_cache,
    ):
        mock_get_cache.return_value = None
        result = await get_user_by_uid(mock_session, mock_user.uid)

        assert result.id == mock_user.id
        assert result.username == mock_user.username
        mock_set_cache.assert_called_once()


@pytest.mark.asyncio
async def test_get_user_by_uid_not_found():
    mock_session = AsyncMock(spec=AsyncSession)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result

    with patch.object(
        CacheService, "get_user", new_callable=AsyncMock
    ) as mock_get_cache:
        mock_get_cache.return_value = None

        with pytest.raises(NotFoundError) as exc_info:
            await get_user_by_uid(mock_session, "non-existent-uid")

        assert exc_info.value.message == "Пользователь не найден"


@pytest.mark.asyncio
async def test_get_user_by_email_success(mock_user):
    mock_session = AsyncMock(spec=AsyncSession)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_user
    mock_session.execute.return_value = mock_result

    result = await get_user_by_email(mock_session, "test@example.com")

    assert result is not None
    assert result.email == "test@example.com"


@pytest.mark.asyncio
async def test_get_user_by_name_success(mock_user):
    mock_session = AsyncMock(spec=AsyncSession)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_user
    mock_session.execute.return_value = mock_result

    result = await get_user_by_name(mock_session, "test_user")

    assert result is not None
    assert result.username == "test_user"


@pytest.mark.asyncio
async def test_create_user_success(user_create_data):
    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock()

    # Mock the user that will be returned after creation
    mock_user = User(
        id=1,
        uid=str(uuid.uuid4()),
        username=user_create_data["username"],
        email=user_create_data["email"],
        hashed_password=b"hashed_password",
        is_active=True,
        is_subscribed=False,
    )

    def mock_add(user):
        user.id = mock_user.id
        user.uid = mock_user.uid
        user.is_active = mock_user.is_active
        user.is_subscribed = mock_user.is_subscribed
        return user

    mock_session.add.side_effect = mock_add

    with patch(
        "src.app.core.repo.user.get_password_hash", return_value=b"hashed_password"
    ):
        user_create = UserCreate(**user_create_data)
        result = await create_user(mock_session, user_create)

    assert result is not None
    assert result.id == 1
    assert result.username == user_create_data["username"]
    assert result.email == user_create_data["email"]
    mock_session.add.assert_called_once()
    mock_session.commit.assert_called_once()
    mock_session.refresh.assert_called_once()


@pytest.mark.asyncio
async def test_create_user_database_error(user_create_data):
    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.commit = AsyncMock(side_effect=SQLAlchemyError("Database error"))
    mock_session.rollback = AsyncMock()

    with patch(
        "src.app.core.repo.user.get_password_hash", return_value=b"hashed_password"
    ):
        with patch("src.app.core.repo.user.log") as mock_logger:
            with pytest.raises(DatabaseError) as exc_info:
                user_create = UserCreate(**user_create_data)
                await create_user(mock_session, user_create)

            assert exc_info.value.message == "Ошибка при создании пользователя"

            mock_session.rollback.assert_called_once()

            mock_logger.error.assert_called()


@pytest.mark.asyncio
async def test_choose_subscribe_status_success(mock_user):
    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.commit = AsyncMock()

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_user
    mock_session.execute.return_value = mock_result

    user_public = UserPublic.model_validate(mock_user)
    await choose_subscribe_status(user_public, mock_session, False)

    assert not mock_user.is_subscribed
    mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_choose_subscribe_status_not_found():
    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.commit = AsyncMock()

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result

    user_public = UserPublic(
        id=999,
        uid=str(uuid.uuid4()),
        username="nonexistent",
        email="nonexistent@example.com",
    )

    with pytest.raises(NotFoundError) as exc_info:
        await choose_subscribe_status(user_public, mock_session, False)

    assert exc_info.value.message == "Пользователь не найден"


@pytest.mark.asyncio
async def test_update_user_password_success():
    """Тест успешного обновления пароля"""
    from src.app.core.repo.user import update_user_password

    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.commit = AsyncMock()

    # cоздаём mock пользователя
    mock_user = User(
        id=1,
        uid="test-uid-123",
        username="testuser",
        email="test@example.com",
        hashed_password=b"old_hashed_password",
        is_active=True,
    )

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_user
    mock_session.execute.return_value = mock_result

    with patch(
        "src.app.core.repo.user.get_password_hash", return_value=b"new_hashed_password"
    ):
        await update_user_password(mock_session, "test-uid-123", "NewPassword123!")

    # проверяем, что пароль был обновлён
    assert mock_user.hashed_password == b"new_hashed_password"
    mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_update_user_password_user_not_found():
    """Тест обновления пароля для несуществующего пользователя"""
    from src.app.core.repo.user import update_user_password

    mock_session = AsyncMock(spec=AsyncSession)

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result

    with pytest.raises(NotFoundError) as exc_info:
        await update_user_password(mock_session, "non-existent-uid", "NewPassword123!")

    assert exc_info.value.message == "Пользователь не найден"


@pytest.mark.asyncio
async def test_update_user_password_database_error():
    """Тест обработки ошибки БД при обновлении пароля"""
    from src.app.core.repo.user import update_user_password

    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.execute.side_effect = SQLAlchemyError("Database connection error")
    mock_session.rollback = AsyncMock()

    with pytest.raises(DatabaseError) as exc_info:
        await update_user_password(mock_session, "test-uid-123", "NewPassword123!")

    assert exc_info.value.message == "Ошибка при обновлении пароля"
    mock_session.rollback.assert_called_once()


@pytest.mark.asyncio
async def test_update_user_password_commit_error():
    """Тест обработки ошибки commit при обновлении пароля"""
    from src.app.core.repo.user import update_user_password

    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.commit.side_effect = SQLAlchemyError("Commit failed")
    mock_session.rollback = AsyncMock()

    mock_user = User(
        id=1,
        uid="test-uid-123",
        username="testuser",
        email="test@example.com",
        hashed_password=b"old_hashed_password",
        is_active=True,
    )

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_user
    mock_session.execute.return_value = mock_result

    with patch(
        "src.app.core.repo.user.get_password_hash", return_value=b"new_hashed_password"
    ):
        with pytest.raises(DatabaseError) as exc_info:
            await update_user_password(mock_session, "test-uid-123", "NewPassword123!")

    assert exc_info.value.message == "Ошибка при обновлении пароля"
    mock_session.rollback.assert_called_once()


@pytest.mark.asyncio
async def test_update_user_password_hash_verification():
    """Тест на то, что новый хеш действительно применяется"""
    from src.app.core.repo.user import update_user_password

    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.commit = AsyncMock()

    old_hash = b"old_hashed_password"
    new_hash = b"new_hashed_password"

    mock_user = User(
        id=1,
        uid="test-uid-123",
        username="testuser",
        email="test@example.com",
        hashed_password=old_hash,
        is_active=True,
    )

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_user
    mock_session.execute.return_value = mock_result

    with patch(
        "src.app.core.repo.user.get_password_hash", return_value=new_hash
    ) as mock_hash:
        await update_user_password(mock_session, "test-uid-123", "NewPassword123!")

        # проверяем, что get_password_hash был вызван с правильным паролем
        mock_hash.assert_called_once_with("NewPassword123!")

        # проверяем, что хеш изменился
        assert mock_user.hashed_password == new_hash
        assert mock_user.hashed_password != old_hash


@pytest.mark.asyncio
async def test_update_user_password_with_empty_password():
    """Тест обновления с пустым паролем"""
    from src.app.core.repo.user import update_user_password

    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.commit = AsyncMock()

    mock_user = User(
        id=1,
        uid="test-uid-123",
        username="testuser",
        email="test@example.com",
        hashed_password=b"old_hashed_password",
        is_active=True,
    )

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_user
    mock_session.execute.return_value = mock_result

    # пустой пароль должен быть обработан (хотя валидация должна быть на уровне схемы)
    with patch(
        "src.app.core.repo.user.get_password_hash", return_value=b"empty_hash"
    ) as mock_hash:
        await update_user_password(mock_session, "test-uid-123", "")

        mock_hash.assert_called_once_with("")
        assert mock_user.hashed_password == b"empty_hash"
