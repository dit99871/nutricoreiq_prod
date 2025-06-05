import pytest
import re
from unittest.mock import patch
from src.app.utils.security import (
    generate_csrf_token,
    generate_csp_nonce,
    generate_hash_token,
)
from src.app.core.config import settings


# Тесты для generate_csrf_token
def test_generate_csrf_token_type_and_length():
    """Проверяет, что CSRF-токен — это строка длиной 64 символа (32 байта в hex)."""
    token = generate_csrf_token()
    assert isinstance(token, str)
    assert len(token) == 64  # 32 байта * 2 символа на байт


def test_generate_csrf_token_hex_format():
    """Проверяет, что CSRF-токен состоит только из шестнадцатеричных символов."""
    token = generate_csrf_token()
    assert re.match(r"^[0-9a-fA-F]{64}$", token) is not None


def test_generate_csrf_token_randomness():
    """Проверяет, что два последовательных вызова возвращают разные токены."""
    token1 = generate_csrf_token()
    token2 = generate_csrf_token()
    assert token1 != token2


# Тесты для generate_csp_nonce
def test_generate_csp_nonce_type_and_length():
    """Проверяет, что CSP nonce — это строка длиной около 43 символов (32 байта в Base64)."""
    nonce = generate_csp_nonce()
    assert isinstance(nonce, str)
    assert 42 <= len(nonce) <= 44  # Base64-кодирование 32 байтов даёт ~43 символа


def test_generate_csp_nonce_url_safe():
    """Проверяет, что CSP nonce состоит только из URL-безопасных символов."""
    nonce = generate_csp_nonce()
    assert re.match(r"^[A-Za-z0-9_-]+$", nonce) is not None


def test_generate_csp_nonce_randomness():
    """Проверяет, что два последовательных вызова возвращают разные nonce."""
    nonce1 = generate_csp_nonce()
    nonce2 = generate_csp_nonce()
    assert nonce1 != nonce2


# Тесты для generate_hash_token
def test_generate_hash_token_type_and_length():
    """Проверяет, что хэш-токен — это строка длиной 64 символа (SHA256)."""
    with patch.object(settings.redis, "salt", "test_salt"):
        token = generate_hash_token("test_token")
    assert isinstance(token, str)
    assert len(token) == 64  # SHA256 в шестнадцатеричном формате


def test_generate_hash_token_hex_format():
    """Проверяет, что хэш-токен состоит только из шестнадцатеричных символов."""
    with patch.object(settings.redis, "salt", "test_salt"):
        token = generate_hash_token("test_token")
    assert re.match(r"^[0-9a-fA-F]{64}$", token) is not None


def test_generate_hash_token_determinism():
    """Проверяет, что одинаковый токен и соль дают одинаковый хэш."""
    with patch.object(settings.redis, "salt", "test_salt"):
        hash1 = generate_hash_token("test_token")
        hash2 = generate_hash_token("test_token")
    assert hash1 == hash2


def test_generate_hash_token_different_tokens():
    """Проверяет, что разные токены дают разные хэши."""
    with patch.object(settings.redis, "salt", "test_salt"):
        hash1 = generate_hash_token("test_token1")
        hash2 = generate_hash_token("test_token2")
    assert hash1 != hash2


def test_generate_hash_token_different_salts():
    """Проверяет, что одинаковый токен с разными солями даёт разные хэши."""
    with patch.object(settings.redis, "salt", "salt1"):
        hash1 = generate_hash_token("test_token")
    with patch.object(settings.redis, "salt", "salt2"):
        hash2 = generate_hash_token("test_token")
    assert hash1 != hash2


def test_generate_hash_token_uses_salt():
    """Проверяет, что соль из настроек используется в хэшировании."""
    with patch.object(settings.redis, "salt", "known_salt"):
        hash_with_salt = generate_hash_token("test_token")
    # Вычисляем ожидаемый хэш напрямую
    import hashlib

    expected_hash = hashlib.sha256("test_tokenknown_salt".encode()).hexdigest()
    assert hash_with_salt == expected_hash
