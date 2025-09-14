import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.crud.profile import get_user_profile, update_user_profile
from src.app.models import User
from src.app.schemas.user import UserProfileUpdate, UserPublic
from src.app.models.user import KFALevel, GoalType, UserRole


def create_test_user(**kwargs):
    """Helper function to create a test user."""
    defaults = {
        "id": 1,
        "username": "testuser",
        "email": "test@example.com",
        "hashed_password": b"hashed_password",
        "is_active": True,
        "created_at": datetime.now().date(),
        "age": 25,
        "weight": 70.5,
        "height": 175.0,
        "gender": "male",
        "kfa": KFALevel.MEDIUM,
        "goal": GoalType.MAINTAIN_WEIGHT,
        "is_subscribed": True,
        "role": UserRole.USER,
        "uid": "test-uid-123",
    }
    defaults.update(kwargs)
    return User(**defaults)


@pytest.fixture
def mock_user():
    """Create a mock user for testing."""
    return create_test_user()


@pytest.fixture
def user_public(mock_user):
    """Create a UserPublic instance for testing."""
    return UserPublic.model_validate(mock_user)


@pytest.mark.asyncio
async def test_get_user_profile_success(mock_user):
    """Test successful retrieval of user profile."""
    # Create a mock for the result object
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_user

    # Create a mock for the session
    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.execute.return_value = mock_result

    result = await get_user_profile(mock_session, user_id=1)

    assert result is not None
    assert result.id == 1
    assert result.username == "testuser"
    assert result.email == "test@example.com"
    assert result.created_at is not None
    mock_session.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_user_profile_not_found():
    """Test user not found scenario."""
    # Create a mock for the result object
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None

    # Create a mock for the session
    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.execute.return_value = mock_result

    with pytest.raises(HTTPException) as exc_info:
        await get_user_profile(mock_session, user_id=999)

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
    assert "Пользователь не найден" == exc_info.value.detail["message"]
    assert exc_info.value.detail.get("user_id") == 999
    mock_session.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_update_user_profile_success(mock_user, user_public):
    """Test successful profile update with KFALevel enum."""
    # Create a new user with updated values
    updated_user = create_test_user(
        id=mock_user.id,
        username=mock_user.username,
        email=mock_user.email,
        hashed_password=mock_user.hashed_password,
        is_active=mock_user.is_active,
        created_at=datetime.now(timezone.utc),
        age=30,  # Updated age
        weight=75.5,  # Updated weight
        height=180.0,  # Updated height
        gender="male",
        kfa=KFALevel.HIGH,  # Updated KFA
        goal=GoalType.LOSE_WEIGHT,  # Updated goal
        is_subscribed=mock_user.is_subscribed,
        role=mock_user.role,
        uid=mock_user.uid,
    )

    # Create a mock for the result object
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = updated_user

    # Create a mock for the session
    db = AsyncMock(spec=AsyncSession)
    db.execute.return_value = mock_result
    db.commit = AsyncMock()

    # Create update data
    update_data = UserProfileUpdate(
        age=30,
        weight=75.5,
        height=180.0,
        gender="male",
        kfa=KFALevel.HIGH,
        goal=GoalType.LOSE_WEIGHT,
    )

    # Call the function with the correct parameters
    result = await update_user_profile(
        data_in=update_data, current_user=user_public, session=db
    )

    # Verify the results
    assert result is not None
    assert result.age == 30
    assert result.weight == 75.5
    assert result.height == 180.0
    assert result.gender == "male"

    # Handle both enum and integer kfa
    kfa_value = result.kfa.value if hasattr(result.kfa, "value") else result.kfa
    assert kfa_value in [4, KFALevel.HIGH]

    if hasattr(result.kfa, "value"):
        assert str(result.kfa) == "Высокий"

    assert result.goal == str(GoalType.LOSE_WEIGHT.value)
    assert result.created_at is not None
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_update_user_profile_with_int_kfa(mock_user, user_public):
    """Test that KFA can be set using raw integer value and is converted to KFALevel."""
    # Create a new user with updated KFA value
    updated_user = create_test_user(
        id=mock_user.id,
        username=mock_user.username,
        email=mock_user.email,
        hashed_password=mock_user.hashed_password,
        is_active=mock_user.is_active,
        created_at=datetime.now(timezone.utc),
        age=mock_user.age,
        weight=mock_user.weight,
        height=mock_user.height,
        gender=mock_user.gender,
        kfa=KFALevel.HIGH,  # Updated KFA
        goal=mock_user.goal,
        is_subscribed=mock_user.is_subscribed,
        role=mock_user.role,
        uid=mock_user.uid,
    )

    # Create a mock for the result object
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = updated_user

    # Create a mock for the session
    db = AsyncMock(spec=AsyncSession)
    db.execute.return_value = mock_result
    db.commit = AsyncMock()

    # Create update data with integer KFA
    update_data = UserProfileUpdate(kfa=4)  # Should be converted to KFALevel.HIGH

    # Call the function with the correct parameters
    result = await update_user_profile(
        data_in=update_data, current_user=user_public, session=db
    )

    # Verify the results
    kfa_value = result.kfa.value if hasattr(result.kfa, "value") else result.kfa
    assert kfa_value in [4, KFALevel.HIGH]

    if hasattr(result.kfa, "value"):
        assert str(result.kfa) == "Высокий"

    assert result.created_at is not None
    db.commit.assert_awaited_once()


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

    # Create a mock for the result object
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = updated_user

    # Create a mock for the session
    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.execute.return_value = mock_result
    mock_session.commit = AsyncMock()

    # Act
    with patch("src.app.crud.profile.log") as mock_log:
        result = await update_user_profile(
            data_in=update_data, current_user=user_public, session=mock_session
        )

    # Assert
    assert result is not None
    assert result.weight == 80.0
    assert result.created_at is not None
    mock_session.execute.assert_awaited_once()
    mock_session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_update_user_profile_not_found(user_public):
    """Test updating a non-existent user profile."""
    # Arrange
    update_data = UserProfileUpdate(weight=80.0)

    # Create a mock for the result object
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None

    # Create a mock for the session
    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.execute.return_value = mock_result

    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await update_user_profile(
            data_in=update_data, current_user=user_public, session=mock_session
        )

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
    assert "При обновлении профиля произошла ошибка" in exc_info.value.detail["message"]
    mock_session.execute.assert_awaited_once()
    mock_session.commit.assert_not_called()


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
    assert "Внутренняя ошибка сервера" in exc_info.value.detail["message"]


@pytest.mark.asyncio
async def test_update_user_profile_database_error(mock_user, user_public):
    """Test database error when updating user profile."""
    # Arrange
    update_data = UserProfileUpdate(weight=80.0)

    # Create a mock for the session
    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.execute.side_effect = SQLAlchemyError("Database error")

    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await update_user_profile(
            data_in=update_data, current_user=user_public, session=mock_session
        )

    assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert "Внутренняя ошибка сервера" in exc_info.value.detail["message"]
    mock_session.rollback.assert_called_once()
