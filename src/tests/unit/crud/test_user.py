import logging
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from src.app.crud.user import (
    _get_user_by_filter,
    get_user_by_uid,
    get_user_by_email,
    get_user_by_name,
    create_user,
)
from src.app.db.models import User
from src.app.schemas.user import UserCreate, UserResponse

log = logging.getLogger("user_crud")


# Временные фикстуры для отладки
@pytest.fixture
def test_user():
    """Фикстура для создания тестового пользователя."""
    return User(
        id=1,
        uid="test-uid",
        username="testuser",
        email="test@example.com",
        hashed_password=b"hashed_pwd",
        gender="female",
        age=25,
        weight=60.0,
        height=165.0,
        kfa="2",
        goal="Снижение веса",
        is_active=True,
        role="user",
        created_at="05.06.2025 10:22:00",
    )


@pytest.fixture
def user_response():
    """Фикстура для создания тестового ответа пользователя."""
    return UserResponse(
        id=1,
        uid="test-uid",
        username="testuser",
        email="test@example.com",
        hashed_password=b"hashed_pwd",
    )


# Тесты для _get_user_by_filter
@pytest.mark.asyncio
async def test_get_user_by_filter_success(test_user):
    """Проверяет успешное получение пользователя по фильтру."""
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = test_user
    mock_session.execute.return_value = mock_result

    result = await _get_user_by_filter(
        session=mock_session, filter_condition=User.uid == "test-uid"
    )

    assert isinstance(result, UserResponse)
    assert result.username == "testuser"
    assert result.email == "test@example.com"
    assert result.id == 1
    assert result.uid == "test-uid"


@pytest.mark.asyncio
async def test_get_user_by_filter_not_found():
    """Проверяет поведение, если пользователь не найден."""
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result

    result = await _get_user_by_filter(
        session=mock_session, filter_condition=User.uid == "nonexistent-uid"
    )

    assert result is None


@pytest.mark.asyncio
async def test_get_user_by_filter_sqlalchemy_error():
    """Проверяет обработку ошибок SQLAlchemy."""
    mock_session = AsyncMock()
    mock_session.execute.side_effect = SQLAlchemyError("DB error")

    with pytest.raises(HTTPException) as exc_info:
        await _get_user_by_filter(
            session=mock_session, filter_condition=User.uid == "test-uid"
        )

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
    assert "DB error getting user" in exc_info.value.detail


@pytest.mark.asyncio
async def test_get_user_by_filter_unexpected_error():
    """Проверяет обработку неожиданных ошибок."""
    mock_session = AsyncMock()
    mock_session.execute.side_effect = Exception("Unexpected error")

    with pytest.raises(HTTPException) as exc_info:
        await _get_user_by_filter(
            session=mock_session, filter_condition=User.uid == "test-uid"
        )

    assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert "Unexpected error getting user" in exc_info.value.detail


# Тесты для get_user_by_uid
@pytest.mark.asyncio
async def test_get_user_by_uid_success(user_response):
    """Проверяет успешное получение пользователя по UID."""
    mock_session = AsyncMock()
    with patch(
        "src.app.crud.user._get_user_by_filter", return_value=user_response
    ) as mock_get_user:
        result = await get_user_by_uid(session=mock_session, uid="test-uid")

    assert isinstance(result, UserResponse)
    assert result.username == "testuser"
    assert result.uid == "test-uid"


@pytest.mark.asyncio
async def test_get_user_by_uid_not_found():
    """Проверяет поведение, если пользователь не найден по UID."""
    mock_session = AsyncMock()
    with patch("src.app.crud.user._get_user_by_filter", return_value=None):
        with pytest.raises(HTTPException) as exc_info:
            await get_user_by_uid(session=mock_session, uid="nonexistent-uid")

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
    assert "User not found in db by uid" in exc_info.value.detail


@pytest.mark.asyncio
async def test_get_user_by_uid_sqlalchemy_error():
    """Проверяет обработку ошибок SQLAlchemy при получении по UID."""
    mock_session = AsyncMock()
    with patch(
        "src.app.crud.user._get_user_by_filter",
        side_effect=HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="DB error"
        ),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await get_user_by_uid(session=mock_session, uid="test-uid")

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
    assert "DB error" in exc_info.value.detail


# Тесты для get_user_by_email
@pytest.mark.asyncio
async def test_get_user_by_email_success(user_response):
    """Проверяет успешное получение пользователя по email."""
    mock_session = AsyncMock()
    with patch("src.app.crud.user._get_user_by_filter", return_value=user_response):
        result = await get_user_by_email(session=mock_session, email="test@example.com")

    assert isinstance(result, UserResponse)
    assert result.email == "test@example.com"


@pytest.mark.asyncio
async def test_get_user_by_email_not_found():
    """Проверяет поведение, если пользователь не найден по email."""
    mock_session = AsyncMock()
    with patch("src.app.crud.user._get_user_by_filter", return_value=None):
        result = await get_user_by_email(
            session=mock_session, email="nonexistent@example.com"
        )

    assert result is None


@pytest.mark.asyncio
async def test_get_user_by_email_sqlalchemy_error():
    """Проверяет обработку ошибок SQLAlchemy при получении по email."""
    mock_session = AsyncMock()
    with patch(
        "src.app.crud.user._get_user_by_filter",
        side_effect=HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="DB error"
        ),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await get_user_by_email(session=mock_session, email="test@example.com")

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
    assert "DB error" in exc_info.value.detail


# Тесты для get_user_by_name
@pytest.mark.asyncio
async def test_get_user_by_name_success(user_response):
    """Проверяет успешное получение пользователя по имени."""
    mock_session = AsyncMock()
    with patch("src.app.crud.user._get_user_by_filter", return_value=user_response):
        result = await get_user_by_name(session=mock_session, user_name="testuser")

    assert isinstance(result, UserResponse)
    assert result.username == "testuser"


@pytest.mark.asyncio
async def test_get_user_by_name_not_found():
    """Проверяет поведение, если пользователь не найден по имени."""
    mock_session = AsyncMock()
    with patch("src.app.crud.user._get_user_by_filter", return_value=None):
        with pytest.raises(HTTPException) as exc_info:
            await get_user_by_name(session=mock_session, user_name="nonexistent")

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
    assert "User not found in db by name" in exc_info.value.detail


@pytest.mark.asyncio
async def test_get_user_by_name_sqlalchemy_error():
    """Проверяет обработку ошибок SQLAlchemy при получении по имени."""
    mock_session = AsyncMock()
    with patch(
        "src.app.crud.user._get_user_by_filter",
        side_effect=HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="DB error"
        ),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await get_user_by_name(session=mock_session, user_name="testuser")

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
    assert "DB error" in exc_info.value.detail


# Тесты для create_user
@pytest.mark.asyncio
async def test_create_user_success():
    """Проверяет успешное создание пользователя."""
    user_in = UserCreate(
        username="newuser", email="newuser@example.com", password="password123"
    )
    mock_session = AsyncMock()
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock()

    with patch("src.app.crud.user.get_password_hash", return_value=b"hashed_password"):
        result = await create_user(session=mock_session, user_in=user_in)

    assert result == user_in
    mock_session.add.assert_called_once()
    mock_session.commit.assert_called_once()
    mock_session.refresh.assert_called_once()


@pytest.mark.asyncio
async def test_create_user_sqlalchemy_error():
    """Проверяет обработку ошибок SQLAlchemy при создании пользователя."""
    user_in = UserCreate(
        username="newuser", email="newuser@example.com", password="password123"
    )
    mock_session = AsyncMock()
    mock_session.commit.side_effect = SQLAlchemyError("DB error")

    with patch("src.app.crud.user.get_password_hash", return_value=b"hashed_password"):
        with pytest.raises(HTTPException) as exc_info:
            await create_user(session=mock_session, user_in=user_in)

    assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert "DB error" in exc_info.value.detail
    mock_session.rollback.assert_called_once()


@pytest.mark.asyncio
async def test_create_user_unexpected_error():
    """Проверяет обработку неожиданных ошибок при создании пользователя."""
    user_in = UserCreate(
        username="newuser", email="newuser@example.com", password="password123"
    )
    mock_session = AsyncMock()
    mock_session.commit.side_effect = Exception("Unexpected error")

    with patch("src.app.crud.user.get_password_hash", return_value=b"hashed_password"):
        with pytest.raises(HTTPException) as exc_info:
            await create_user(session=mock_session, user_in=user_in)

    assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert "Unexpected error" in exc_info.value.detail
    mock_session.rollback.assert_called_once()
