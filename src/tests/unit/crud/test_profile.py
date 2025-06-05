import logging
import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi import HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from src.app.crud.profile import get_user_profile, update_user_profile
from src.app.db.models import User
from src.app.schemas.user import UserAccount, UserProfile, UserResponse

log = logging.getLogger("profile_crud")


# Фикстуры для тестов
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


@pytest.fixture
def user_profile():
    """Фикстура для создания тестового профиля пользователя."""
    return UserProfile(
        gender="male",
        age=30,
        weight=70.0,
        height=170.0,
        kfa="3",
        goal="Увеличение веса",
    )


# Тесты для get_user_profile
@pytest.mark.asyncio
async def test_get_user_profile_success(test_user):
    """Проверяет успешное получение профиля пользователя."""
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = test_user
    mock_session.execute.return_value = mock_result

    result = await get_user_profile(session=mock_session, user_id=1)

    assert isinstance(result, UserAccount)
    assert result.username == "testuser"
    assert result.email == "test@example.com"
    assert result.gender == "female"
    assert result.age == 25
    assert result.weight == 60.0
    assert result.height == 165.0
    assert result.kfa == "2"
    assert result.goal == "Снижение веса"


@pytest.mark.asyncio
async def test_get_user_profile_not_found():
    """Проверяет поведение, если пользователь не найден."""
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result

    with pytest.raises(HTTPException) as exc_info:
        await get_user_profile(session=mock_session, user_id=999)

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
    assert "User not found in db for user_id 999" in exc_info.value.detail


@pytest.mark.asyncio
async def test_get_user_profile_inactive(test_user):
    """Проверяет поведение, если пользователь неактивен."""
    test_user.is_active = False
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = (
        None  # filter(is_active=True) вернёт None
    )
    mock_session.execute.return_value = mock_result

    with pytest.raises(HTTPException) as exc_info:
        await get_user_profile(session=mock_session, user_id=1)

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_get_user_profile_sqlalchemy_error():
    """Проверяет обработку ошибок SQLAlchemy."""
    mock_session = AsyncMock()
    mock_session.execute.side_effect = SQLAlchemyError("DB error")

    with pytest.raises(HTTPException) as exc_info:
        await get_user_profile(session=mock_session, user_id=1)

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
    assert "DB error getting user" in exc_info.value.detail


@pytest.mark.asyncio
async def test_get_user_profile_unexpected_error():
    """Проверяет обработку неожиданных ошибок."""
    mock_session = AsyncMock()
    mock_session.execute.side_effect = Exception("Unexpected error")

    with pytest.raises(HTTPException) as exc_info:
        await get_user_profile(session=mock_session, user_id=1)

    assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert "Unexpected error getting user" in exc_info.value.detail


# Тесты для update_user_profile
@pytest.mark.asyncio
async def test_update_user_profile_success(user_response, user_profile):
    """Проверяет успешное обновление профиля пользователя."""
    mock_session = AsyncMock()
    mock_result = MagicMock()
    updated_user = User(
        id=1,
        uid="test-uid",
        username="testuser",
        email="test@example.com",
        hashed_password=b"hashed_pwd",
        gender=user_profile.gender,
        age=user_profile.age,
        weight=user_profile.weight,
        height=user_profile.height,
        kfa=user_profile.kfa,
        goal=user_profile.goal,
        is_active=True,
        role="user",
        created_at="05.06.2025 10:22:00",
    )
    mock_result.scalar_one_or_none.return_value = updated_user
    mock_session.execute.return_value = mock_result
    mock_session.commit = AsyncMock()

    result = await update_user_profile(
        data_in=user_profile,
        current_user=user_response,
        session=mock_session,
    )

    assert isinstance(result, UserAccount)
    assert result.username == "testuser"
    assert result.gender == "male"
    assert result.age == 30
    assert result.weight == 70.0
    assert result.height == 170.0
    assert result.kfa == "3"
    assert result.goal == "Увеличение веса"


@pytest.mark.asyncio
async def test_update_user_profile_not_found(user_response, user_profile):
    """Проверяет поведение, если обновление не удалось."""
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result
    print("Before calling update_user_profile")
    with pytest.raises(HTTPException) as exc_info:
        await update_user_profile(
            data_in=user_profile,
            current_user=user_response,
            session=mock_session,
        )
    print("After calling update_user_profile")
    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
    assert "User not updated" in exc_info.value.detail


@pytest.mark.asyncio
async def test_update_user_profile_sqlalchemy_error(user_response, user_profile):
    """Проверяет обработку ошибок SQLAlchemy."""
    mock_session = AsyncMock()
    mock_session.execute.side_effect = SQLAlchemyError("DB error")
    mock_session.rollback = AsyncMock()

    result = await update_user_profile(
        data_in=user_profile,
        current_user=user_response,
        session=mock_session,
    )

    assert result is None


@pytest.mark.asyncio
async def test_update_user_profile_unexpected_error(user_response, user_profile):
    """Проверяет обработку неожиданных ошибок."""
    mock_session = AsyncMock()
    mock_session.execute.side_effect = Exception("Unexpected error")
    mock_session.rollback = AsyncMock()

    result = await update_user_profile(
        data_in=user_profile,
        current_user=user_response,
        session=mock_session,
    )

    assert result is None
