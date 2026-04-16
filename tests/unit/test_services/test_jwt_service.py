"""
Тесты для JWT Service.
"""

from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import jwt
import pytest
from fastapi import Request
from jwt import ExpiredSignatureError, PyJWTError

from src.app.core.constants import ACCESS_TOKEN_TYPE, REFRESH_TOKEN_TYPE, TOKEN_TYPE_FIELD
from src.app.core.exceptions import AuthenticationError, ExpiredTokenException, ExternalServiceError
from src.app.core.schemas.user import UserPublic
from src.app.core.services import jwt_service


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
def mock_request():
    """Создает мок для Request."""
    request = MagicMock(spec=Request)
    request.cookies = {}
    return request


# --- encode_jwt ---


@patch("src.app.core.services.jwt_service.settings")
@patch("jwt.encode")
def test_encode_jwt_success(mock_jwt_encode, mock_settings):
    """Тест успешного кодирования JWT."""
    mock_settings.auth.private_key_path.read_text.return_value = "private_key"
    mock_settings.auth.algorithm = "RS256"
    mock_settings.auth.access_token_expires = 15
    mock_jwt_encode.return_value = "encoded_token"

    payload = {"sub": "test-uid", "username": "test"}

    result = jwt_service.encode_jwt(payload)

    assert result == "encoded_token"
    mock_jwt_encode.assert_called_once()


@patch("src.app.core.services.jwt_service.settings")
@patch("jwt.encode")
def test_encode_jwt_with_timedelta(mock_jwt_encode, mock_settings):
    """Тест кодирования JWT с timedelta."""
    mock_settings.auth.private_key_path.read_text.return_value = "private_key"
    mock_settings.auth.algorithm = "RS256"
    mock_jwt_encode.return_value = "encoded_token"

    payload = {"sub": "test-uid"}
    expire_timedelta = timedelta(hours=1)

    result = jwt_service.encode_jwt(payload, expire_timedelta=expire_timedelta)

    assert result == "encoded_token"


@patch("src.app.core.services.jwt_service.settings")
def test_encode_jwt_file_not_found(mock_settings):
    """Тест обработки ошибки отсутствия файла с приватным ключом."""
    mock_settings.auth.private_key_path.read_text.side_effect = FileNotFoundError("Key not found")

    with pytest.raises(ExternalServiceError) as exc_info:
        jwt_service.encode_jwt({"sub": "test"})

    assert "Ошибка авторизации" in str(exc_info.value)


@patch("src.app.core.services.jwt_service.settings")
def test_encode_jwt_jwt_error(mock_settings):
    """Тест обработки ошибки JWT при кодировании."""
    mock_settings.auth.private_key_path.read_text.return_value = "invalid_key"
    mock_settings.auth.algorithm = "RS256"
    
    with patch("jwt.encode", side_effect=PyJWTError("Encoding error")):
        with pytest.raises(ExternalServiceError) as exc_info:
            jwt_service.encode_jwt({"sub": "test"})

    assert "Ошибка авторизации" in str(exc_info.value)


# --- decode_jwt ---


@patch("src.app.core.services.jwt_service.settings")
@patch("jwt.decode")
def test_decode_jwt_success(mock_jwt_decode, mock_settings):
    """Тест успешного декодирования JWT."""
    mock_settings.auth.public_key_path.read_text.return_value = "public_key"
    mock_settings.auth.algorithm = "RS256"
    mock_jwt_decode.return_value = {"sub": "test-uid", "username": "test"}

    result = jwt_service.decode_jwt("valid_token")

    assert result == {"sub": "test-uid", "username": "test"}


def test_decode_jwt_none_token():
    """Тест декодирования None токена."""
    result = jwt_service.decode_jwt(None)
    assert result is None


@patch("src.app.core.services.jwt_service.settings")
def test_decode_jwt_file_not_found(mock_settings):
    """Тест обработки ошибки отсутствия файла с публичным ключом."""
    mock_settings.auth.public_key_path.read_text.side_effect = FileNotFoundError("Key not found")
    mock_settings.auth.algorithm = "RS256"

    with pytest.raises(ExternalServiceError) as exc_info:
        jwt_service.decode_jwt("token")

    assert "Ошибка авторизации" in str(exc_info.value)


@patch("src.app.core.services.jwt_service.settings")
@patch("jwt.decode")
def test_decode_jwt_expired(mock_jwt_decode, mock_settings):
    """Тест обработки истекшего токена."""
    mock_settings.auth.public_key_path.read_text.return_value = "public_key"
    mock_settings.auth.algorithm = "RS256"
    mock_jwt_decode.side_effect = ExpiredSignatureError("Token expired")

    with pytest.raises(ExpiredTokenException):
        jwt_service.decode_jwt("expired_token")


@patch("src.app.core.services.jwt_service.settings")
@patch("jwt.decode")
def test_decode_jwt_invalid_token(mock_jwt_decode, mock_settings):
    """Тест обработки неверного токена."""
    mock_settings.auth.public_key_path.read_text.return_value = "public_key"
    mock_settings.auth.algorithm = "RS256"
    mock_jwt_decode.side_effect = PyJWTError("Invalid token")

    with pytest.raises(AuthenticationError):
        jwt_service.decode_jwt("invalid_token")


# --- create_jwt ---


@patch("src.app.core.services.jwt_service.encode_jwt")
def test_create_jwt_success(mock_encode_jwt):
    """Тест успешного создания JWT."""
    mock_encode_jwt.return_value = "encoded_token"
    token_data = {"sub": "test-uid"}

    result = jwt_service.create_jwt(ACCESS_TOKEN_TYPE, token_data)

    assert result == "encoded_token"
    mock_encode_jwt.assert_called_once()


@patch("src.app.core.services.jwt_service.encode_jwt")
def test_create_jwt_with_timedelta(mock_encode_jwt):
    """Тест создания JWT с timedelta."""
    mock_encode_jwt.return_value = "encoded_token"
    token_data = {"sub": "test-uid"}
    expire_timedelta = timedelta(hours=1)

    result = jwt_service.create_jwt(ACCESS_TOKEN_TYPE, token_data, expire_timedelta=expire_timedelta)

    assert result == "encoded_token"
    call_args = mock_encode_jwt.call_args
    assert call_args[1]["expire_timedelta"] == expire_timedelta


# --- create_access_jwt ---


@patch("src.app.core.services.jwt_service.create_jwt")
@patch("src.app.core.services.jwt_service.settings")
def test_create_access_jwt_success(mock_settings, mock_create_jwt, user_public):
    """Тест успешного создания access токена."""
    mock_settings.auth.access_token_expires = 15
    mock_create_jwt.return_value = "access_token"

    result = jwt_service.create_access_jwt(user_public)

    assert result == "access_token"
    mock_create_jwt.assert_called_once()
    call_args = mock_create_jwt.call_args[1]
    assert call_args["token_type"] == ACCESS_TOKEN_TYPE
    assert "sub" in call_args["token_data"]
    assert call_args["token_data"]["username"] == "testuser"
    assert call_args["token_data"]["email"] == "test@example.com"


# --- create_refresh_jwt ---


@pytest.mark.asyncio
@patch("src.app.core.services.jwt_service.create_jwt")
@patch("src.app.core.services.jwt_service.add_refresh_jwt_to_redis")
@patch("src.app.core.services.jwt_service.settings")
async def test_create_refresh_jwt_success(mock_settings, mock_add_to_redis, mock_create_jwt, user_public):
    """Тест успешного создания refresh токена."""
    mock_settings.auth.refresh_token_expires = 30
    mock_create_jwt.return_value = "refresh_token"
    mock_add_to_redis.return_value = None

    result = await jwt_service.create_refresh_jwt(user_public)

    assert result == "refresh_token"
    mock_create_jwt.assert_called_once()
    call_args = mock_create_jwt.call_args[1]
    assert call_args["token_type"] == REFRESH_TOKEN_TYPE
    mock_add_to_redis.assert_called_once()


@pytest.mark.asyncio
@patch("src.app.core.services.jwt_service.create_jwt")
@patch("src.app.core.services.jwt_service.add_refresh_jwt_to_redis")
@patch("src.app.core.services.jwt_service.settings")
async def test_create_refresh_jwt_uses_timedelta(mock_settings, mock_add_to_redis, mock_create_jwt, user_public):
    """Тест что create_refresh_jwt использует timedelta для истечения."""
    mock_settings.auth.refresh_token_expires = 30
    mock_create_jwt.return_value = "refresh_token"
    mock_add_to_redis.return_value = None

    await jwt_service.create_refresh_jwt(user_public)

    call_args = mock_create_jwt.call_args[1]
    assert "expire_timedelta" in call_args
    assert isinstance(call_args["expire_timedelta"], timedelta)


# --- get_jwt_from_cookies ---


@pytest.mark.asyncio
async def test_get_jwt_from_cookies_success(mock_request):
    """Тест успешного получения токена из cookies."""
    mock_request.cookies = {ACCESS_TOKEN_TYPE: "access_token_value"}

    result = await jwt_service.get_jwt_from_cookies(mock_request)

    assert result == "access_token_value"


@pytest.mark.asyncio
async def test_get_jwt_from_cookies_not_found(mock_request):
    """Тест когда токен отсутствует в cookies."""
    mock_request.cookies = {}

    result = await jwt_service.get_jwt_from_cookies(mock_request)

    assert result is None


@pytest.mark.asyncio
async def test_get_jwt_from_cookies_custom_type(mock_request):
    """Тест получения токена указанного типа."""
    mock_request.cookies = {REFRESH_TOKEN_TYPE: "refresh_token_value"}

    result = await jwt_service.get_jwt_from_cookies(mock_request, token_type=REFRESH_TOKEN_TYPE)

    assert result == "refresh_token_value"


# --- get_jwt_payload ---


@pytest.mark.asyncio
@patch("src.app.core.services.jwt_service.decode_jwt")
async def test_get_jwt_payload_success(mock_decode_jwt):
    """Тест успешного получения payload."""
    mock_decode_jwt.return_value = {"sub": "test-uid", "username": "test"}

    result = await jwt_service.get_jwt_payload("valid_token")

    assert result == {"sub": "test-uid", "username": "test"}


@pytest.mark.asyncio
@patch("src.app.core.services.jwt_service.decode_jwt")
async def test_get_jwt_payload_none(mock_decode_jwt):
    """Тест когда decode_jwt возвращает None."""
    mock_decode_jwt.return_value = None

    with pytest.raises(AuthenticationError):
        await jwt_service.get_jwt_payload("token")


@pytest.mark.asyncio
@patch("src.app.core.services.jwt_service.decode_jwt")
async def test_get_jwt_payload_decode_error(mock_decode_jwt):
    """Тест когда decode_jwt выбрасывает исключение."""
    from src.app.core.constants import CREDENTIAL_EXCEPTION
    mock_decode_jwt.side_effect = AuthenticationError("Decode error")

    with pytest.raises(AuthenticationError):
        await jwt_service.get_jwt_payload("token")
