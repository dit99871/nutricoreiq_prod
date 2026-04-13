"""
Тесты для утилит аутентификации.
"""

import base64
import hashlib
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import bcrypt
import pytest
from fastapi.responses import JSONResponse

from src.app.core.schemas.user import UserPublic
from src.app.core.utils import auth


def test_get_password_hash_returns_bytes():
    hashed = auth.get_password_hash("test_password")
    assert isinstance(hashed, bytes)
    assert len(hashed) > 0


def test_get_password_hash_unique_hashes():
    """Разные соли дают разные хеши для одного пароля."""
    password = "test_password"
    assert auth.get_password_hash(password) != auth.get_password_hash(password)


def test_get_password_hash_empty_password():
    hashed = auth.get_password_hash("")
    assert isinstance(hashed, bytes)
    assert auth.verify_password("", hashed)


@pytest.mark.parametrize("password, min_length", [
    ("short", 60),
    ("a" * 100, 60),
    ("!@#$%^&*()_+", 60),
    ("1234567890", 60),
])
def test_get_password_hash_various_inputs(password, min_length):
    hashed = auth.get_password_hash(password)
    assert isinstance(hashed, bytes)
    assert len(hashed) >= min_length


def test_verify_password_correct():
    password = "test_password"
    hashed = auth.get_password_hash(password)
    assert auth.verify_password(password, hashed) is True


def test_verify_password_incorrect():
    hashed = auth.get_password_hash("test_password")
    assert auth.verify_password("wrong_password", hashed) is False


def test_verify_password_invalid_hash():
    assert auth.verify_password("test_password", b"invalid_hash") is False


def test_verify_password_empty_hash():
    assert auth.verify_password("test_password", b"") is False


@pytest.mark.parametrize("password, hashed_password, expected", [
    (
        "password",
        bcrypt.hashpw(
            base64.b64encode(hashlib.sha256(b"password").digest()),
            bcrypt.gensalt(),
        ),
        True,
    ),
    (
        "wrong",
        bcrypt.hashpw(
            base64.b64encode(hashlib.sha256(b"password").digest()),
            bcrypt.gensalt(),
        ),
        False,
    ),
])
def test_verify_password_with_precomputed_hashes(password, hashed_password, expected):
    assert auth.verify_password(password, hashed_password) == expected


def test_verify_password_legacy_correct():
    """Старый метод верифицирует хеши, сделанные без SHA256."""
    password = "TestPass123!"
    old_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
    assert auth._verify_password_legacy(password, old_hash) is True


def test_verify_password_legacy_incorrect_password():
    old_hash = bcrypt.hashpw("correct".encode(), bcrypt.gensalt())
    assert auth._verify_password_legacy("wrong", old_hash) is False


def test_verify_password_legacy_new_hash():
    """Старый метод НЕ проходит для новых хешей (SHA256+base64)."""
    password = "TestPass123!"
    new_hash = auth.get_password_hash(password)
    assert auth._verify_password_legacy(password, new_hash) is False


def test_verify_password_legacy_invalid_hash():
    assert auth._verify_password_legacy("password", b"invalid") is False


def test_needs_rehash_old_format():
    """Старый хеш (без SHA256) должен требовать перехеширования."""
    password = "TestPass123!"
    old_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
    assert auth.needs_rehash(password, old_hash) is True


def test_needs_rehash_new_format():
    """Новый хеш (с SHA256) — перехеширование не нужно."""
    password = "TestPass123!"
    new_hash = auth.get_password_hash(password)
    assert auth.needs_rehash(password, new_hash) is False


def test_needs_rehash_wrong_password():
    """Неверный пароль не должен триггерить rehash."""
    old_hash = bcrypt.hashpw("correct".encode(), bcrypt.gensalt())
    assert auth.needs_rehash("wrong", old_hash) is False


def test_needs_rehash_invalid_hash():
    assert auth.needs_rehash("password", b"invalid") is False


def test_needs_rehash_empty_password():
    old_hash = bcrypt.hashpw(b"", bcrypt.gensalt())
    assert auth.needs_rehash("", old_hash) is True


@pytest.fixture
def mock_user():
    return UserPublic(
        id=1,
        uid="test-uid-123",
        email="test@example.com",
        username="testuser",
    )


@pytest.mark.asyncio
@patch("src.app.core.utils.auth.create_access_jwt")
@patch("src.app.core.utils.auth.create_refresh_jwt")
async def test_create_response_returns_json_response(
    mock_refresh_jwt, mock_access_jwt, mock_user
):
    mock_access_jwt.return_value = "access_token"
    mock_refresh_jwt.return_value = "refresh_token"

    with patch("src.app.core.utils.auth.settings") as mock_settings:
        mock_settings.auth.refresh_token_expires = 30
        mock_settings.auth.access_token_expires = 15
        mock_settings.env.env = "test"

        response = await auth.create_response(mock_user)

    assert isinstance(response, JSONResponse)
    assert response.status_code == 200


@pytest.mark.asyncio
@patch("src.app.core.utils.auth.create_access_jwt")
@patch("src.app.core.utils.auth.create_refresh_jwt")
async def test_create_response_sets_two_cookies(
    mock_refresh_jwt, mock_access_jwt, mock_user
):
    mock_access_jwt.return_value = "access_token"
    mock_refresh_jwt.return_value = "refresh_token"

    mock_response = MagicMock(spec=JSONResponse)
    mock_response.headers = {}

    with patch("src.app.core.utils.auth.JSONResponse", return_value=mock_response):
        with patch("src.app.core.utils.auth.settings") as mock_settings:
            mock_settings.auth.refresh_token_expires = 30
            mock_settings.auth.access_token_expires = 15
            mock_settings.env.env = "test"

            await auth.create_response(mock_user)

    assert mock_response.set_cookie.call_count == 2


@pytest.mark.asyncio
@patch("src.app.core.utils.auth.create_access_jwt")
@patch("src.app.core.utils.auth.create_refresh_jwt")
async def test_create_response_cookies_are_httponly(
    mock_refresh_jwt, mock_access_jwt, mock_user
):
    mock_access_jwt.return_value = "access_token"
    mock_refresh_jwt.return_value = "refresh_token"

    mock_response = MagicMock(spec=JSONResponse)
    mock_response.headers = {}

    with patch("src.app.core.utils.auth.JSONResponse", return_value=mock_response):
        with patch("src.app.core.utils.auth.settings") as mock_settings:
            mock_settings.auth.refresh_token_expires = 30
            mock_settings.auth.access_token_expires = 15
            mock_settings.env.env = "test"

            await auth.create_response(mock_user)

    for call in mock_response.set_cookie.call_args_list:
        assert call[1]["httponly"] is True


@pytest.mark.asyncio
@patch("src.app.core.utils.auth.create_access_jwt")
@patch("src.app.core.utils.auth.create_refresh_jwt")
async def test_create_response_secure_in_prod(
    mock_refresh_jwt, mock_access_jwt, mock_user
):
    mock_access_jwt.return_value = "access_token"
    mock_refresh_jwt.return_value = "refresh_token"

    mock_response = MagicMock(spec=JSONResponse)
    mock_response.headers = {}

    with patch("src.app.core.utils.auth.JSONResponse", return_value=mock_response):
        with patch("src.app.core.utils.auth.settings") as mock_settings:
            mock_settings.auth.refresh_token_expires = 30
            mock_settings.auth.access_token_expires = 15
            mock_settings.env.env = "prod"

            await auth.create_response(mock_user)

    for call in mock_response.set_cookie.call_args_list:
        assert call[1]["secure"] is True
        assert call[1]["samesite"] == "strict"


@pytest.mark.asyncio
@patch("src.app.core.utils.auth.create_access_jwt")
@patch("src.app.core.utils.auth.create_refresh_jwt")
async def test_create_response_token_expiry(
    mock_refresh_jwt, mock_access_jwt, mock_user
):
    """Проверяем что сроки действия токенов рассчитываются корректно."""
    mock_access_jwt.return_value = "access_token"
    mock_refresh_jwt.return_value = "refresh_token"

    mock_response = MagicMock(spec=JSONResponse)
    mock_response.headers = {}

    fixed_now = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

    with patch("src.app.core.utils.auth.JSONResponse", return_value=mock_response):
        with patch("src.app.core.utils.auth.dt") as mock_dt:
            mock_dt.datetime.now.return_value = fixed_now
            mock_dt.timedelta = timedelta
            mock_dt.UTC = timezone.utc

            with patch("src.app.core.utils.auth.settings") as mock_settings:
                mock_settings.auth.refresh_token_expires = 30
                mock_settings.auth.access_token_expires = 15
                mock_settings.env.env = "test"

                await auth.create_response(mock_user)

    calls = mock_response.set_cookie.call_args_list
    access_call = next(c for c in calls if c[1]["key"] == "access_token")
    refresh_call = next(c for c in calls if c[1]["key"] == "refresh_token")

    assert access_call[1]["expires"] == datetime(2024, 1, 1, 12, 15, 0, tzinfo=timezone.utc)
    assert refresh_call[1]["expires"] == datetime(2024, 1, 31, 12, 0, 0, tzinfo=timezone.utc)


@pytest.mark.asyncio
@patch("src.app.core.utils.auth.create_access_jwt")
async def test_create_response_error_propagates(mock_access_jwt, mock_user):
    mock_access_jwt.side_effect = Exception("Token creation failed")
    with pytest.raises(Exception, match="Token creation failed"):
        await auth.create_response(mock_user)