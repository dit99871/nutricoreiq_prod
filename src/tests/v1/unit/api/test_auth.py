import pytest
from fastapi import HTTPException, Request
from fastapi.responses import RedirectResponse
from unittest.mock import MagicMock, patch
from src.app.api.v1.auth import (
    register_user,
    login,
    logout,
    refresh_token,
    change_password,
)
from src.app.schemas.user import UserCreate, UserResponse
from src.app.services.auth import add_tokens_to_response, update_password


@pytest.mark.asyncio
async def test_register_user_success(mock_db_session):
    """Тестирует успешную регистрацию пользователя."""
    user_in = UserCreate(
        username="newuser", email="newuser@example.com", password="password123"
    )
    with patch(
        "src.app.api.v1.auth.get_user_by_email", return_value=None
    ) as mock_get_user, patch(
        "src.app.api.v1.auth.create_user", return_value=user_in
    ) as mock_create_user:
        result = await register_user(user_in, mock_db_session)
        assert result == user_in
        mock_get_user.assert_called_once_with(mock_db_session, user_in.email)
        mock_create_user.assert_called_once_with(mock_db_session, user_in)


@pytest.mark.asyncio
async def test_register_user_duplicate_email(mock_db_session):
    """Тестирует ошибку при дубликате email."""
    user_in = UserCreate(
        username="newuser", email="newuser@example.com", password="password123"
    )
    with patch("src.app.api.v1.auth.get_user_by_email", return_value=user_in):
        with pytest.raises(HTTPException) as exc:
            await register_user(user_in, mock_db_session)
        assert exc.value.status_code == 400
        assert exc.value.detail == "Email already registered"


@pytest.mark.asyncio
async def test_login_success(mock_db_session):
    """Тестирует успешный логин."""
    form_data = MagicMock()
    form_data.username = "newuser"
    form_data.password = "password123"
    user = UserResponse(
        uid="user1", id=1, username="newuser", email="newuser@example.com"
    )
    response = {"access_token": "access", "refresh_token": "refresh"}

    with patch(
        "src.app.api.v1.auth.authenticate_user", return_value=user
    ) as mock_authenticate, patch(
        "src.app.api.v1.auth.add_tokens_to_response", return_value=response
    ) as mock_add_tokens:
        result = await login(form_data, mock_db_session)
        assert result == response
        mock_authenticate.assert_called_once_with(
            mock_db_session, "newuser", "password123"
        )
        mock_add_tokens.assert_called_once_with(user)


@pytest.mark.asyncio
async def test_login_invalid_credentials(mock_db_session):
    """Тестирует ошибку при неверных учетных данных."""
    form_data = MagicMock()
    form_data.username = "newuser"
    form_data.password = "wrongpassword"
    with patch(
        "src.app.api.v1.auth.authenticate_user",
        side_effect=HTTPException(status_code=401, detail="Invalid credentials"),
    ):
        with pytest.raises(HTTPException) as exc:
            await login(form_data, mock_db_session)
        assert exc.value.status_code == 401
        assert exc.value.detail == "Invalid credentials"


@pytest.mark.asyncio
async def test_logout_success(mock_redis):
    """Тестирует успешный выход."""
    request = MagicMock()
    request.cookies.get.return_value = "refresh_token"
    user = UserResponse(
        uid="user1", id=1, username="newuser", email="newuser@example.com"
    )
    with patch("src.app.api.v1.auth.revoke_refresh_token") as mock_revoke:
        response = await logout(request, user, mock_redis)
        assert isinstance(response, RedirectResponse)
        assert response.status_code == 303
        assert response.headers["location"] == "/"
        # Проверяем удаление куков через заголовки
        set_cookie_headers = response.headers.getlist("Set-Cookie")
        # Проверяем наличие заголовков для удаления access_token и refresh_token
        access_token_deleted = any(
            "access_token=" in header.lower() and "max-age=0" in header.lower()
            for header in set_cookie_headers
        )
        refresh_token_deleted = any(
            "refresh_token=" in header.lower() and "max-age=0" in header.lower()
            for header in set_cookie_headers
        )
        assert (
            access_token_deleted
        ), f"access_token not deleted, headers: {set_cookie_headers}"
        assert (
            refresh_token_deleted
        ), f"refresh_token not deleted, headers: {set_cookie_headers}"
        mock_revoke.assert_called_once_with(user.uid, "refresh_token", mock_redis)


@pytest.mark.asyncio
async def test_logout_no_refresh_token(mock_redis):
    """Тестирует ошибку при отсутствии refresh-токена."""
    request = MagicMock()
    request.cookies.get.return_value = None
    user = UserResponse(
        uid="user1", id=1, username="newuser", email="newuser@example.com"
    )
    with patch("src.app.api.v1.auth.revoke_refresh_token") as mock_revoke:
        with pytest.raises(HTTPException) as exc:
            await logout(request, user, mock_redis)
        assert exc.value.status_code == 401
        assert exc.value.detail == "No refresh token in cookies"
        mock_revoke.assert_not_called()


@pytest.mark.asyncio
async def test_refresh_token_success(mock_db_session, mock_redis):
    """Тестирует успешное обновление токенов."""
    request = MagicMock()
    request.cookies.get.return_value = "refresh_token"
    user = UserResponse(
        uid="user1", id=1, username="newuser", email="newuser@example.com"
    )
    with patch(
        "src.app.api.v1.auth.get_current_auth_user_for_refresh", return_value=user
    ), patch(
        "src.app.api.v1.auth.create_access_jwt", return_value="new_access_token"
    ), patch(
        "src.app.api.v1.auth.create_refresh_jwt", return_value="new_refresh_token"
    ), patch(
        "src.app.api.v1.auth.create_response",
        return_value={
            "access_token": "new_access_token",
            "refresh_token": "new_refresh_token",
        },
    ):
        response = await refresh_token(request, mock_db_session, mock_redis)
        assert response == {
            "access_token": "new_access_token",
            "refresh_token": "new_refresh_token",
        }


@pytest.mark.asyncio
async def test_refresh_token_no_token(mock_db_session, mock_redis):
    """Тестирует ошибку при отсутствии refresh-токена."""
    request = MagicMock()
    request.cookies.get.return_value = None
    with patch(
        "src.app.api.v1.auth.get_current_auth_user_for_refresh"
    ) as mock_get_user:
        with pytest.raises(HTTPException) as exc:
            await refresh_token(request, mock_db_session, mock_redis)
        assert exc.value.status_code == 401
        assert exc.value.detail == "No refresh token found in cookies"
        mock_get_user.assert_not_called()


@pytest.mark.asyncio
async def test_change_password_success():
    """Тестирует успешную смену пароля."""
    user = UserResponse(
        uid="user1", id=1, username="newuser", email="newuser@example.com"
    )
    response = {"access_token": "new_access", "refresh_token": "new_refresh"}
    with patch(
        "src.app.api.v1.auth.update_password", return_value=response
    ) as mock_update:
        result = await change_password(user)
        assert result == response
        mock_update.assert_called_once_with(user)
