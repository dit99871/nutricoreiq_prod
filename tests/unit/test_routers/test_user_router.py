"""
Тесты для user router.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import Request

from src.app.core.exceptions import ExpiredTokenException, ValidationError
from src.app.core.models.user import GoalType, KFALevel
from src.app.core.schemas.user import UserProfileUpdate, UserPublic


@pytest.fixture
def mock_request():
    """Создает мок для Request."""
    request = MagicMock(spec=Request)
    request.state = MagicMock()
    request.state.csp_nonce = "test_nonce"
    return request


@pytest.fixture
def mock_user_service():
    """Создает мок для UserService."""
    service = MagicMock()
    service.calculate_user_nutrients = MagicMock()
    return service


@pytest.fixture
def mock_db_session():
    """Создает мок для DB session."""
    session = AsyncMock()
    return session


@pytest.fixture
def user_public():
    """Валидные данные публичного пользователя."""
    return UserPublic(
        id=1,
        uid="test-uid-123",
        username="testuser",
        email="test@example.com",
    )


@pytest.fixture
def user_profile():
    """Мок профиля пользователя."""
    user = MagicMock()
    user.id = 1
    user.username = "testuser"
    user.email = "test@example.com"
    user.is_subscribed = True
    return user


# --- read_current_user ---


@pytest.mark.asyncio
async def test_read_current_user_success(user_public):
    """Тест успешного получения текущего пользователя."""
    from src.app.routers.user import read_current_user

    result = await read_current_user(user_public)

    assert result == {"username": "testuser", "email": "test@example.com"}


@pytest.mark.asyncio
async def test_read_current_user_no_user():
    """Тест получения текущего пользователя без авторизации."""
    from src.app.routers.user import read_current_user

    with pytest.raises(ExpiredTokenException):
        await read_current_user(None)


# --- get_profile ---


@pytest.mark.asyncio
@patch("src.app.routers.user.get_user_profile")
@patch("src.app.routers.user.templates.TemplateResponse")
async def test_get_profile_success(
    mock_template_response, mock_get_user_profile, mock_request, user_profile, mock_user_service, mock_db_session
):
    """Тест успешного получения профиля."""
    from src.app.routers.user import get_profile

    mock_get_user_profile.return_value = user_profile
    mock_user_service.calculate_user_nutrients.return_value = {
        "tdee": 2000,
        "nutrients": {"carbs": 250, "proteins": 100, "fats": 67}
    }
    mock_template_response.return_value = MagicMock()

    result = await get_profile(mock_request, user_profile, mock_db_session, mock_user_service)

    mock_template_response.assert_called_once()
    call_kwargs = mock_template_response.call_args[1]
    assert call_kwargs["name"] == "profile.html"
    assert call_kwargs["request"] == mock_request
    assert call_kwargs["context"]["user"] == user_profile
    assert call_kwargs["context"]["is_filled"] is True
    assert call_kwargs["context"]["tdee"] == 2000
    assert call_kwargs["context"]["KFALevel"] == KFALevel


@pytest.mark.asyncio
@patch("src.app.routers.user.get_user_profile")
@patch("src.app.routers.user.templates.TemplateResponse")
async def test_get_profile_no_user(
    mock_template_response, mock_get_user_profile, mock_request, mock_user_service, mock_db_session
):
    """Тест получения профиля без авторизации."""
    from src.app.routers.user import get_profile

    with pytest.raises(ExpiredTokenException):
        await get_profile(mock_request, None, mock_db_session, mock_user_service)


@pytest.mark.asyncio
@patch("src.app.routers.user.get_user_profile")
@patch("src.app.routers.user.templates.TemplateResponse")
async def test_get_profile_incomplete_profile(
    mock_template_response, mock_get_user_profile, mock_request, user_profile, mock_user_service, mock_db_session
):
    """Тест получения профиля с незаполненными данными."""
    from src.app.routers.user import get_profile

    mock_get_user_profile.return_value = user_profile
    mock_user_service.calculate_user_nutrients.return_value = None
    mock_template_response.return_value = MagicMock()

    result = await get_profile(mock_request, user_profile, mock_db_session, mock_user_service)

    call_kwargs = mock_template_response.call_args[1]
    assert call_kwargs["context"]["is_filled"] is False
    assert call_kwargs["context"]["tdee"] is None
    assert call_kwargs["context"]["nutrients"] is None


# --- update_profile ---


@pytest.mark.asyncio
@patch("src.app.routers.user.update_user_profile")
async def test_update_profile_success(mock_update_user_profile, user_profile, mock_db_session):
    """Тест успешного обновления профиля."""
    from src.app.routers.user import update_profile

    data_in = UserProfileUpdate(
        age=30,
        height=180,
        weight=80,
        kfa_level=KFALevel.MEDIUM,
        goal=GoalType.MAINTAIN_WEIGHT,
    )

    result = await update_profile(data_in, user_profile, mock_db_session)

    assert result == {"message": "Profile updated successfully"}
    mock_update_user_profile.assert_called_once_with(data_in, user_profile, mock_db_session)


@pytest.mark.asyncio
async def test_update_profile_no_user(mock_db_session):
    """Тест обновления профиля без авторизации."""
    from src.app.routers.user import update_profile

    data_in = UserProfileUpdate(
        age=30,
        height=180,
        weight=80,
        kfa_level=KFALevel.MEDIUM,
        goal=GoalType.MAINTAIN_WEIGHT,
    )

    with pytest.raises(ExpiredTokenException):
        await update_profile(data_in, None, mock_db_session)


@pytest.mark.asyncio
async def test_update_profile_invalid_data(user_profile, mock_db_session):
    """Тест обновления профиля с невалидными данными."""
    from src.app.routers.user import update_profile

    with pytest.raises(ValidationError) as exc_info:
        await update_profile(None, user_profile, mock_db_session)

    assert "Произошла ошибка" in str(exc_info.value)


# --- unsubscribe_email_notification ---


@pytest.mark.asyncio
@patch("src.app.routers.user.choose_subscribe_status")
async def test_unsubscribe_success(mock_choose_subscribe_status, user_profile, mock_db_session):
    """Тест успешной отписки от уведомлений."""
    from src.app.routers.user import unsubscribe_email_notification

    result = await unsubscribe_email_notification(user_profile, mock_db_session)

    mock_choose_subscribe_status.assert_called_once_with(user_profile, mock_db_session, False)


@pytest.mark.asyncio
async def test_unsubscribe_no_user(mock_db_session):
    """Тест отписки без авторизации."""
    from src.app.routers.user import unsubscribe_email_notification

    with pytest.raises(ExpiredTokenException):
        await unsubscribe_email_notification(None, mock_db_session)


# --- subscribe_email_notification ---


@pytest.mark.asyncio
@patch("src.app.routers.user.choose_subscribe_status")
async def test_subscribe_success(mock_choose_subscribe_status, user_profile, mock_db_session):
    """Тест успешной подписки на уведомления."""
    from src.app.routers.user import subscribe_email_notification

    result = await subscribe_email_notification(user_profile, mock_db_session)

    mock_choose_subscribe_status.assert_called_once_with(user_profile, mock_db_session, True)


@pytest.mark.asyncio
async def test_subscribe_no_user(mock_db_session):
    """Тест подписки без авторизации."""
    from src.app.routers.user import subscribe_email_notification

    with pytest.raises(ExpiredTokenException):
        await subscribe_email_notification(None, mock_db_session)


# --- login_get ---


@pytest.mark.asyncio
async def test_login_get_redirect():
    """Тест редиректа на главную страницу."""
    from src.app.routers.user import login_get

    result = await login_get()

    assert result.status_code == 307
    assert result.headers["location"] == "/?action=unsubscribe"
