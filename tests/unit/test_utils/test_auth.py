import base64
import bcrypt
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock
import hashlib

from fastapi.responses import JSONResponse

from src.app.core.utils import auth
from src.app.core.schemas.user import UserPublic


def test_get_password_hash_returns_bytes():
    """
    Test that get_password_hash returns a bytes object.
    """
    password = "test_password"
    hashed_password = auth.get_password_hash(password)
    assert isinstance(hashed_password, bytes)
    assert len(hashed_password) > 0  # гарантирует, что хэш не пустой


def test_get_password_hash_unique_hashes():
    """
    Test that get_password_hash generates different
    hashes for the same password due to random salt.
    """
    password = "test_password"
    hash1 = auth.get_password_hash(password)
    hash2 = auth.get_password_hash(password)
    assert hash1 != hash2  # разные salt генерируют разные хэши


def test_get_password_hash_empty_password():
    """
    Test get_password_hash with an empty password.
    """
    hashed_password = auth.get_password_hash("")
    assert isinstance(hashed_password, bytes)
    assert auth.verify_password("", hashed_password)  # проверка на пустое значение


def test_verify_password_correct():
    """
    Test verify_password with correct password.
    """
    password = "test_password"
    hashed_password = auth.get_password_hash(password)
    assert auth.verify_password(password, hashed_password) is True


def test_verify_password_incorrect():
    """
    Test verify_password with incorrect password.
    """
    password = "test_password"
    hashed_password = auth.get_password_hash(password)
    assert auth.verify_password("wrong_password", hashed_password) is False


def test_verify_password_invalid_hashed_password():
    """
    Test verify_password with invalid hashed password.
    """
    assert auth.verify_password("test_password", b"invalid_hash") is False


def test_verify_password_empty_hashed_password():
    """
    Test verify_password with empty hashed password.
    """
    assert auth.verify_password("test_password", b"") is False


def test_verify_password_none_hashed_password():
    """
    Test verify_password with None as hashed password.
    """
    assert auth.verify_password("test_password", None) is False


@pytest.mark.parametrize(
    "password, expected_length",
    [
        ("short", 60),  # Минимальная длина пароля
        ("a" * 100, 60),  # Длинный пароль
        ("!@#$%^&*()_+", 60),  # Специальные символы
        ("1234567890", 60),  # Только цифры
    ],
)
def test_get_password_hash_various_inputs(password, expected_length):
    """
    Test get_password_hash with various password inputs.
    Проверяем, что функция корректно обрабатывает пароли разной длины и состава.
    """
    hashed = auth.get_password_hash(password)
    assert isinstance(hashed, bytes)
    assert len(hashed) >= expected_length


@pytest.mark.parametrize(
    "password, hashed_password, expected",
    [
        (
            "password",
            bcrypt.hashpw(base64.b64encode(hashlib.sha256(b"password").digest()), bcrypt.gensalt()),
            True,
        ),
        (
            "wrong",
            bcrypt.hashpw(base64.b64encode(hashlib.sha256(b"password").digest()), bcrypt.gensalt()),
            False,
        ),
    ],
)
def test_verify_password_with_precomputed_hashes(password, hashed_password, expected):
    """
    Test verify_password with precomputed bcrypt hashes.
    Проверяем верификацию с заранее известными хешами.
    """
    # Используем нашу функцию verify_password, которая применяет SHA256 + base64
    result = auth.verify_password(password, hashed_password)
    assert isinstance(result, bool)
    assert result == expected


@pytest.mark.asyncio
@patch("src.app.core.utils.auth.create_access_jwt")
@patch("src.app.core.utils.auth.create_refresh_jwt")
async def test_create_response_success(mock_refresh_jwt, mock_access_jwt):
    """
    Test successful creation of authentication response.
    Проверяем успешное создание ответа с токенами.
    """
    # Arrange
    mock_access_jwt.return_value = "test_access_token"
    mock_refresh_jwt.return_value = "test_refresh_token"

    user = UserPublic(
        id=1,
        uid="test-uid-123",
        email="test@example.com",
        username="testuser",
    )

    # Создаем мок для объекта ответа
    mock_response = MagicMock(spec=JSONResponse)
    mock_response.headers = {}

    # Заменяем JSONResponse на наш мок
    with patch(
        "src.app.core.utils.auth.JSONResponse", return_value=mock_response
    ) as mock_orjson:
        with patch("src.app.core.utils.auth.dt") as mock_dt:
            fixed_now = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
            mock_dt.datetime.now.return_value = fixed_now
            mock_dt.timedelta = timedelta

            with patch("src.app.core.utils.auth.settings") as mock_settings:
                mock_settings.auth.refresh_token_expires = 30
                mock_settings.auth.access_token_expires = 15
                mock_settings.env.env = "test"

                await auth.create_response(user)

    # Проверяем, что JSONResponse был вызван с правильными параметрами
    mock_orjson.assert_called_once_with(
        status_code=200,
        headers={
            "Cache-Control": "no-store",
            "Pragma": "no-cache",
        },
        content={"message": "Success"},
    )

    # Проверяем, что set_cookie был вызван дважды (для access и refresh токенов)
    assert mock_response.set_cookie.call_count == 2

    # Получаем все вызовы set_cookie
    set_cookie_calls = mock_response.set_cookie.call_args_list

    # Проверяем куки access токена
    access_call = next(
        call for call in set_cookie_calls if call[1]["key"] == "access_token"
    )
    assert access_call[1]["value"] == "test_access_token"
    assert access_call[1]["httponly"] is True
    assert access_call[1]["secure"] is False  # потому что env=test
    assert access_call[1]["samesite"] == "lax"

    # Проверяем куки refresh токена
    refresh_call = next(
        call for call in set_cookie_calls if call[1]["key"] == "refresh_token"
    )
    assert refresh_call[1]["value"] == "test_refresh_token"
    assert refresh_call[1]["httponly"] is True


@pytest.mark.asyncio
@patch("src.app.core.utils.auth.create_access_jwt")
@patch("src.app.core.utils.auth.create_refresh_jwt")
async def test_create_response_error_handling(mock_refresh_jwt, mock_access_jwt):
    """
    Test error handling in create_response.
    Проверяем обработку ошибок при создании токенов.
    """
    # Arrange
    mock_access_jwt.side_effect = Exception("Token creation failed")
    user = UserPublic(
        id=1,
        uid="test-uid-123",
        email="test@example.com",
        username="testuser",
    )

    # Act & Assert
    with pytest.raises(Exception, match="Token creation failed"):
        await auth.create_response(user)


@pytest.mark.asyncio
@patch("src.app.core.utils.auth.create_access_jwt")
@patch("src.app.core.utils.auth.create_refresh_jwt")
async def test_token_expiration(mock_refresh_jwt, mock_access_jwt):
    """
    Test token expiration settings.
    Проверяем корректность установки срока действия токенов.
    """
    # Arrange
    mock_access_jwt.return_value = "test_access_token"
    mock_refresh_jwt.return_value = "test_refresh_token"

    user = UserPublic(
        id=1,
        uid="test-uid-123",
        email="test@example.com",
        username="testuser",
    )

    # Создаем мок для объекта ответа
    mock_response = MagicMock(spec=JSONResponse)

    # Заменяем JSONResponse на наш мок
    with patch("src.app.core.utils.auth.JSONResponse", return_value=mock_response):
        with patch("src.app.core.utils.auth.dt") as mock_dt:
            fixed_now = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
            mock_dt.datetime.now.return_value = fixed_now
            mock_dt.timedelta = timedelta

            with patch("src.app.core.utils.auth.settings") as mock_settings:
                mock_settings.auth.refresh_token_expires = 30  # дней
                mock_settings.auth.access_token_expires = 15  # минут
                mock_settings.env.env = "test"

                await auth.create_response(user)

    # Получаем все вызовы set_cookie
    set_cookie_calls = mock_response.set_cookie.call_args_list

    # Проверяем срок действия access токена (15 минут)
    access_call = next(
        call for call in set_cookie_calls if call[1]["key"] == "access_token"
    )
    assert access_call[1]["expires"] == datetime(
        2023, 1, 1, 12, 15, 0, tzinfo=timezone.utc
    )

    # Проверяем срок действия refresh токена (30 дней)
    refresh_call = next(
        call for call in set_cookie_calls if call[1]["key"] == "refresh_token"
    )
    assert refresh_call[1]["expires"] == datetime(
        2023, 1, 31, 12, 0, 0, tzinfo=timezone.utc
    )
