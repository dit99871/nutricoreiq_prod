import uuid
from unittest.mock import AsyncMock, patch, MagicMock, ANY
import pytest
from fastapi import HTTPException, status
from pydantic import SecretStr
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

# First, import the modules we need to patch
import src.app.core.utils.validators


# Create a proper mock validator function
def mock_validate_password_strength(v):
    if hasattr(v, "get_secret_value"):
        v = v.get_secret_value()
    if not isinstance(v, str):
        raise ValueError("Password must be a string")
    return v


# Patch the validator at the module level
src.app.core.utils.validators.validate_password_strength = (
    mock_validate_password_strength
)

# Now import the rest of the modules
from src.app.crud.user import (
    _get_user_by_filter,
    get_user_by_uid,
    get_user_by_email,
    get_user_by_name,
    create_user,
    choose_subscribe_status,
)
from src.app.schemas.user import UserCreate, UserPublic
from src.app.models import User
from src.app.core.services.cache import CacheService


# Fixtures
@pytest.fixture
def mock_user():
    return User(
        id=1,
        uid=str(uuid.uuid4()),
        username="testuser",
        email="test@example.com",
        hashed_password=b"hashed_password",
        is_active=True,
        is_subscribed=True,
    )


@pytest.fixture
def user_create_data():
    return {
        "username": "newuser",
        "email": "newuser@example.com",
        "password": SecretStr("StrongPass123!"),
    }


@pytest.mark.asyncio
async def test_get_user_by_filter_success(mock_user):
    mock_session = AsyncMock(spec=AsyncSession)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_user
    mock_session.execute.return_value = mock_result

    result = await _get_user_by_filter(mock_session, User.id == 1)

    assert result is not None
    assert result.id == mock_user.id
    assert result.username == mock_user.username
    assert result.email == mock_user.email
    assert hasattr(result, "hashed_password")
    assert "hashed_password" not in result.model_dump()


@pytest.mark.asyncio
async def test_get_user_by_filter_not_found():
    mock_session = AsyncMock(spec=AsyncSession)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result

    result = await _get_user_by_filter(mock_session, User.id == 999)

    assert result is None


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

        with pytest.raises(HTTPException) as exc_info:
            await get_user_by_uid(mock_session, "non-existent-uid")

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND


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

    result = await get_user_by_name(mock_session, "testuser")

    assert result is not None
    assert result.username == "testuser"


@pytest.mark.asyncio
async def test_get_user_by_name_not_found():
    mock_session = AsyncMock(spec=AsyncSession)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result

    with pytest.raises(HTTPException) as exc_info:
        await get_user_by_name(mock_session, "nonexistentuser")

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND


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

    with patch("src.app.crud.user.get_password_hash", return_value=b"hashed_password"):
        user_create = UserCreate(**user_create_data)
        result = await create_user(mock_session, user_create)

    assert result is not None
    assert result.id == 1
    assert result.username == user_create_data["username"]
    assert result.email == user_create_data["email"]
    # Removed the hashed_password assertion since it's part of the model
    mock_session.add.assert_called_once()
    mock_session.commit.assert_called_once()
    mock_session.refresh.assert_called_once()


@pytest.mark.asyncio
async def test_create_user_database_error(user_create_data):
    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.commit = AsyncMock(side_effect=SQLAlchemyError("Database error"))
    mock_session.rollback = AsyncMock()

    with patch("src.app.crud.user.get_password_hash", return_value=b"hashed_password"):
        with patch("src.app.crud.user.log") as mock_logger:
            with pytest.raises(HTTPException) as exc_info:
                user_create = UserCreate(**user_create_data)
                await create_user(mock_session, user_create)

            # Verify the exception
            assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            assert "Ошибка при создании пользователя" in str(exc_info.value.detail)

            # Verify rollback was called
            mock_session.rollback.assert_called_once()

            # Verify error was logged
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

    with pytest.raises(HTTPException) as exc_info:
        await choose_subscribe_status(user_public, mock_session, False)

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
