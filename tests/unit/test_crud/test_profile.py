import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import date
from uuid import uuid4

from src.app.crud.profile import get_user_profile, update_user_profile
from src.app.models import User
from src.app.models.user import KFALevel, GoalType, UserRole
from src.app.schemas.user import UserProfile, UserProfileUpdate, UserPublic


def create_test_user(**kwargs):
    """Helper function to create a test user with default values."""

    defaults = {
        "id": 1,
        "username": "testuser",
        "email": "test@example.com",
        "hashed_password": b"hashed_password",
        "is_active": True,
        "created_at": date.today(),
        "age": 25,
        "weight": 70.5,
        "height": 175.0,
        "gender": "male",
        "kfa": KFALevel.MEDIUM,
        "goal": GoalType.MAINTAIN_WEIGHT,
        "is_subscribed": True,
        "role": UserRole.USER,
        "uid": str(uuid4()),
    }
    defaults.update(kwargs)
    return User(**{k: v for k, v in defaults.items() if k in User.__table__.columns})


@pytest.fixture
def mock_user():
    """Create a mock user for testing."""
    return create_test_user()


@pytest.fixture
def user_public(mock_user):
    """Create a UserPublic instance from mock user."""
    return UserPublic.model_validate(mock_user)


@pytest.mark.asyncio
async def test_get_user_profile_success(mock_user):
    """Test successful retrieval of user profile."""
    # Arrange
    mock_session = AsyncMock(spec=AsyncSession)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_user
    mock_session.execute.return_value = mock_result

    # Act
    result = await get_user_profile(mock_session, user_id=1)

    # Assert
    assert isinstance(result, UserProfile)
    assert result.id == 1
    assert result.username == "testuser"
    assert result.email == "test@example.com"
    mock_session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_get_user_profile_not_found():
    """Test user not found scenario."""
    # Arrange
    mock_session = AsyncMock(spec=AsyncSession)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result

    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await get_user_profile(mock_session, user_id=999)

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
    assert exc_info.value.detail["message"] == "Пользователь не найден"


@pytest.mark.asyncio
async def test_update_user_profile_success(mock_user, user_public):
    """Test successful profile update."""
    # Arrange
    update_data = UserProfileUpdate(
        age=30,
        weight=75.0,
        height=180.0,
        gender="male",
        kfa="3",
        goal="Поддержание веса",
    )

    # Create a new user with updated data
    updated_user = create_test_user(
        id=mock_user.id,
        username=mock_user.username,
        email=mock_user.email,
        hashed_password=mock_user.hashed_password,
        is_active=mock_user.is_active,
        created_at=mock_user.created_at,
        age=update_data.age,
        weight=update_data.weight,
        height=update_data.height,
        gender=update_data.gender,
        kfa=KFALevel.MEDIUM,
        goal=GoalType.MAINTAIN_WEIGHT,
        is_subscribed=mock_user.is_subscribed,
        role=mock_user.role,
        uid=mock_user.uid,
    )

    mock_session = AsyncMock(spec=AsyncSession)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = updated_user
    mock_session.execute.return_value = mock_result

    # Act
    with patch("src.app.crud.profile.log") as mock_log:
        result = await update_user_profile(
            data_in=update_data, current_user=user_public, session=mock_session
        )

    # Assert
    assert isinstance(result, UserProfile)
    assert result.age == 30
    assert result.weight == 75.0
    assert result.height == 180.0
    assert result.kfa == "3"  # Compare with string value
    assert result.goal == "Поддержание веса"
    mock_session.commit.assert_called_once()
    mock_log.error.assert_not_called()


@pytest.mark.asyncio
async def test_update_user_profile_partial_update(mock_user, user_public):
    """Test partial profile update."""
    # Arrange
    update_data = UserProfileUpdate(weight=80.0)

    # Create a new user with updated weight
    updated_user = create_test_user(
        id=mock_user.id,
        username=mock_user.username,
        email=mock_user.email,
        hashed_password=mock_user.hashed_password,
        is_active=mock_user.is_active,
        created_at=mock_user.created_at,
        age=mock_user.age,
        weight=80.0,  # Updated weight
        height=mock_user.height,
        gender=mock_user.gender,
        kfa=mock_user.kfa,
        goal=mock_user.goal,
        is_subscribed=mock_user.is_subscribed,
        role=mock_user.role,
        uid=mock_user.uid,
    )

    mock_session = AsyncMock(spec=AsyncSession)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = updated_user
    mock_session.execute.return_value = mock_result

    # Act
    with patch("src.app.crud.profile.log") as mock_log:
        result = await update_user_profile(
            data_in=update_data, current_user=user_public, session=mock_session
        )

    # Assert
    assert result.weight == 80.0
    # Other fields should remain unchanged
    assert result.age == 25
    assert result.height == 175.0
    mock_session.commit.assert_called_once()
    mock_log.error.assert_not_called()


@pytest.mark.asyncio
async def test_get_user_profile_database_error():
    """Test database error when getting user profile."""
    # Arrange
    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.execute.side_effect = SQLAlchemyError("Database error")

    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await get_user_profile(mock_session, user_id=1)

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
    assert exc_info.value.detail["message"] == "Внутренняя ошибка сервера"


@pytest.mark.asyncio
async def test_update_user_profile_not_found(user_public):
    """Test updating a non-existent user profile."""
    # Arrange
    update_data = UserProfileUpdate(weight=80.0)

    mock_session = AsyncMock(spec=AsyncSession)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result

    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await update_user_profile(
            data_in=update_data, current_user=user_public, session=mock_session
        )

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
    assert exc_info.value.detail["message"] == "При обновлении профиля произошла ошибка"
    mock_session.commit.assert_not_called()
    mock_session.rollback.assert_not_called()


@pytest.mark.asyncio
async def test_update_user_profile_database_error(mock_user, user_public):
    """Test database error when updating user profile."""
    # Arrange
    update_data = UserProfileUpdate(weight=80.0)

    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.execute.side_effect = SQLAlchemyError("Database error")

    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await update_user_profile(
            data_in=update_data, current_user=user_public, session=mock_session
        )

    assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert exc_info.value.detail["message"] == "Внутренняя ошибка сервера"
    mock_session.rollback.assert_called_once()
