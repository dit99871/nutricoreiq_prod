import pytest
import datetime as dt
import importlib

from fastapi import status
from fastapi.exceptions import HTTPException
from fastapi.responses import ORJSONResponse
from jose import JWTError, ExpiredSignatureError
from pathlib import Path

from src.app.core.config import settings
from src.app.utils.auth import (
    get_password_hash,
    verify_password,
    decode_jwt,
    encode_jwt,
    create_response,
)

# Перезагрузка модуля config для гарантированного обновления settings
importlib.reload(importlib.import_module("src.app.core.config"))


# Тесты для get_password_hash
def test_get_password_hash():
    password = "testpassword"
    hashed_password = get_password_hash(password)
    assert isinstance(hashed_password, bytes)
    assert len(hashed_password) > 0
    assert get_password_hash(password) != get_password_hash(password)


# Тесты для verify_password
def test_verify_password_correct():
    password = "testpassword"
    hashed_password = get_password_hash(password)
    assert verify_password(password, hashed_password) is True


def test_verify_password_incorrect():
    password = "testpassword"
    wrong_password = "wrongpassword"
    hashed_password = get_password_hash(password)
    assert verify_password(wrong_password, hashed_password) is False


# Тесты для decode_jwt
def test_decode_jwt_valid(mocker):
    token = "valid.token.here"
    payload = {"sub": "user123", "exp": dt.datetime.now(dt.UTC).timestamp() + 3600}
    mocker.patch("pathlib.Path.read_text", return_value="mock_public_key")
    mocker.patch("jose.jwt.decode", return_value=payload)
    result = decode_jwt(token)
    assert result == payload
    assert "sub" in result
    assert result["sub"] == "user123"


def test_decode_jwt_none():
    result = decode_jwt(None)
    assert result is None


def test_decode_jwt_file_not_found(mocker):
    token = "valid.token.here"
    mocker.patch(
        "pathlib.Path.read_text", side_effect=FileNotFoundError("Public key not found")
    )
    with pytest.raises(HTTPException) as exc_info:
        decode_jwt(token)
    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
    assert "File with public key not found" in str(exc_info.value.detail)


def test_decode_jwt_expired(mocker):
    token = "expired.token.here"
    mocker.patch("pathlib.Path.read_text", return_value="mock_public_key")
    mocker.patch("jose.jwt.decode", side_effect=ExpiredSignatureError("Token expired"))
    with pytest.raises(HTTPException) as exc_info:
        decode_jwt(token)
    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert "Token has expired" in str(exc_info.value.detail)


def test_decode_jwt_invalid(mocker):
    token = "invalid.token.here"
    mocker.patch("pathlib.Path.read_text", return_value="mock_public_key")
    mocker.patch("jose.jwt.decode", side_effect=JWTError("Invalid token"))
    with pytest.raises(HTTPException) as exc_info:
        decode_jwt(token)
    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert "Invalid token" in str(exc_info.value.detail)


# Тесты для encode_jwt
def test_encode_jwt_valid(mocker):
    payload = {"sub": "user123"}
    mocker.patch("pathlib.Path.read_text", return_value="mock_private_key")
    mocker.patch("jose.jwt.encode", return_value="encoded.token.here")
    token = encode_jwt(payload)
    assert token == "encoded.token.here"
    assert isinstance(token, str)


def test_encode_jwt_with_timedelta(mocker):
    payload = {"sub": "user123"}
    expire_timedelta = dt.timedelta(minutes=10)
    mocker.patch("pathlib.Path.read_text", return_value="mock_private_key")
    mocker.patch("jose.jwt.encode", return_value="encoded.token.here")
    token = encode_jwt(payload, expire_timedelta=expire_timedelta)
    assert token == "encoded.token.here"


def test_encode_jwt_file_not_found(mocker):
    payload = {"sub": "user123"}
    original_path = settings.auth.private_key_path
    settings.auth.private_key_path = Path("/nonexistent/path/private_key.pem")
    try:
        with pytest.raises(HTTPException) as exc_info:
            encode_jwt(payload)
        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert "File with private key not found" in str(exc_info.value.detail)
    finally:
        settings.auth.private_key_path = original_path


def test_encode_jwt_jwt_error(mocker):
    payload = {"sub": "user123"}
    mocker.patch("pathlib.Path.read_text", return_value="mock_private_key")
    mocker.patch("jose.jwt.encode", side_effect=JWTError("JWT encoding error"))
    with pytest.raises(HTTPException) as exc_info:
        encode_jwt(payload)
    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert "JWT error encoding token" in str(exc_info.value.detail)


# Тесты для create_response
def test_create_response(mocker):
    access_token = "access.token.here"
    refresh_token = "refresh.token.here"
    mocker.patch.object(settings.auth, "access_token_expires", 7)
    mocker.patch.object(settings.auth, "refresh_token_expires", 7)
    response = create_response(access_token, refresh_token)
    assert isinstance(response, ORJSONResponse)
    assert response.status_code == status.HTTP_200_OK
    assert response.headers["Cache-Control"] == "no-store"
    assert response.headers["Pragma"] == "no-cache"
    assert response.body == b'{"message":"Login successful"}'
    cookies = response.headers.getlist("set-cookie")
    assert any("access_token=access.token.here" in cookie for cookie in cookies)
    assert any("refresh_token=refresh.token.here" in cookie for cookie in cookies)
    assert any("HttpOnly" in cookie for cookie in cookies)
    assert any("SameSite=lax" in cookie for cookie in cookies)
