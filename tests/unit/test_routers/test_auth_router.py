"""
Тесты для auth router.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import Request, status
from fastapi.security import OAuth2PasswordRequestForm

from src.app.core.exceptions import ConflictError, UserAlreadyExistsError
from src.app.core.schemas.user import UserCreate, UserPublic


@pytest.fixture
def mock_request():
    """Создает мок для Request."""
    request = MagicMock(spec=Request)
    request.state = MagicMock()
    return request


@pytest.fixture
def mock_user_service():
    """Создает мок для UserService."""
    service = AsyncMock()
    return service


@pytest.fixture
def mock_db_session():
    """Создает мок для DB session."""
    session = AsyncMock()
    return session


@pytest.fixture
def mock_redis_service():
    """Создает мок для RedisService."""
    service = AsyncMock()
    return service


@pytest.fixture
def user_create_data():
    """Валидные данные для создания пользователя."""
    return UserCreate(
        username="testuser",
        email="test@example.com",
        password="TestPass123!",
    )


@pytest.fixture
def user_public():
    """Валидные данные публичного пользователя."""
    return UserPublic(
        id=1,
        uid="test-uid-123",
        username="testuser",
        email="test@example.com",
    )


# --- register_user ---


@pytest.mark.asyncio
async def test_register_user_success(
    mock_request, mock_user_service, user_create_data, user_public
):
    """Тест успешной регистрации пользователя."""
    from src.app.routers.auth import register_user

    mock_user_service.register_user.return_value = user_public

    result = await register_user(mock_request, user_create_data, mock_user_service)

    assert result == user_public
    mock_user_service.register_user.assert_called_once_with(
        user_in=user_create_data, request=mock_request
    )


@pytest.mark.asyncio
async def test_register_user_already_exists(
    mock_request, mock_user_service, user_create_data
):
    """Тест регистрации с существующим email."""
    from src.app.routers.auth import register_user

    mock_user_service.register_user.side_effect = UserAlreadyExistsError(
        "User already exists"
    )

    with pytest.raises(ConflictError) as exc_info:
        await register_user(mock_request, user_create_data, mock_user_service)

    assert "Пользователь с таким email уже существует" in str(exc_info.value)


# --- login ---


@pytest.mark.asyncio
async def test_login_success(
    mock_request, mock_user_service, mock_db_session
):
    """Тест успешного входа."""
    from src.app.routers.auth import login
    from fastapi.responses import JSONResponse

    mock_response = JSONResponse(
        content={
            "access_token": "access_token",
            "refresh_token": "refresh_token",
        }
    )
    mock_user_service.login.return_value = mock_response

    form_data = OAuth2PasswordRequestForm(
        username="testuser", password="TestPass123!"
    )

    result = await login(mock_request, form_data, mock_db_session, mock_user_service)

    assert result == mock_response
    mock_user_service.login.assert_called_once_with(
        request=mock_request,
        session=mock_db_session,
        username="testuser",
        password="TestPass123!",
    )


# --- logout ---


@pytest.mark.asyncio
async def test_logout_success(
    mock_request, mock_user_service, mock_redis_service, user_public
):
    """Тест успешного выхода."""
    from src.app.routers.auth import logout
    from fastapi.responses import JSONResponse

    mock_response = JSONResponse(content={"message": "Logged out successfully"})
    mock_user_service.logout.return_value = mock_response

    result = await logout(
        mock_request, user_public, mock_redis_service, mock_user_service
    )

    assert result == mock_response
    mock_user_service.logout.assert_called_once_with(
        mock_request, mock_redis_service, user_public
    )


# --- refresh_token ---


@pytest.mark.asyncio
async def test_refresh_token_success(
    mock_request, mock_user_service, mock_db_session, mock_redis_service
):
    """Тест успешного обновления токенов."""
    from src.app.routers.auth import refresh_token
    from fastapi.responses import JSONResponse

    mock_response = JSONResponse(
        content={
            "access_token": "new_access_token",
            "refresh_token": "new_refresh_token",
        }
    )
    mock_user_service.refresh_jwt.return_value = mock_response

    result = await refresh_token(
        mock_request, mock_db_session, mock_redis_service, mock_user_service
    )

    assert result == mock_response
    mock_user_service.refresh_jwt.assert_called_once_with(
        request=mock_request,
        session=mock_db_session,
        redis_service=mock_redis_service,
    )


# --- change_password ---


@pytest.mark.asyncio
async def test_change_password_success(
    mock_request, mock_user_service, mock_db_session, user_public
):
    """Тест успешной смены пароля."""
    from src.app.routers.auth import change_password
    from src.app.core.schemas.user import PasswordChange
    from fastapi.responses import JSONResponse

    password_data = PasswordChange(
        current_password="OldPass123!", new_password="NewPass123!"
    )

    mock_response = JSONResponse(content={"message": "Password changed successfully"})
    mock_user_service.change_password.return_value = mock_response

    result = await change_password(
        password_data, mock_request, user_public, mock_db_session, mock_user_service
    )

    assert result == mock_response
    mock_user_service.change_password.assert_called_once_with(
        request=mock_request,
        session=mock_db_session,
        user=user_public,
        password_data=password_data,
    )


@pytest.mark.asyncio
async def test_change_password_no_user(mock_request, mock_user_service, mock_db_session):
    """Тест смены пароля без авторизации."""
    from src.app.routers.auth import change_password
    from src.app.core.schemas.user import PasswordChange
    from src.app.core.exceptions import ExpiredTokenException

    password_data = PasswordChange(
        current_password="OldPass123!", new_password="NewPass123!"
    )

    with pytest.raises(ExpiredTokenException):
        await change_password(
            password_data, mock_request, None, mock_db_session, mock_user_service
        )
