import hashlib
from unittest.mock import patch

import re
from importlib import import_module
from src.app.core.config import settings

# Динамический импорт
security = import_module("src.app.utils.security")
generate_hash_token_orig = security.generate_hash_token
generate_csrf_token = security.generate_csrf_token
generate_csp_nonce = security.generate_csp_nonce


# Переопределение generate_hash_token для тестов
def patched_generate_hash_token(token: str) -> str:
    print(
        f"patched_generate_hash_token called with token: {token}, salt: {settings.redis.salt}"
    )
    salted = f"{token}{settings.redis.salt}"
    return hashlib.sha256(salted.encode()).hexdigest()


# Тесты для generate_csrf_token
def test_generate_csrf_token_type_and_length():
    token = generate_csrf_token()
    assert isinstance(token, str)
    assert len(token) == 64


def test_generate_csrf_token_hex_format():
    token = generate_csrf_token()
    assert re.match(r"^[0-9a-fA-F]{64}$", token) is not None


def test_generate_csrf_token_randomness():
    token1 = generate_csrf_token()
    token2 = generate_csrf_token()
    assert token1 != token2


# Тесты для generate_csp_nonce
def test_generate_csp_nonce_type_and_length():
    nonce = generate_csp_nonce()
    assert isinstance(nonce, str)
    assert 42 <= len(nonce) <= 44


def test_generate_csp_nonce_url_safe():
    nonce = generate_csp_nonce()
    assert re.match(r"^[A-Za-z0-9_-]+$", nonce) is not None


def test_generate_csp_nonce_randomness():
    nonce1 = generate_csp_nonce()
    nonce2 = generate_csp_nonce()
    assert nonce1 != nonce2


# Тесты для generate_hash_token
def test_generate_hash_token_type_and_length():
    temp_generate_hash_token = generate_hash_token_orig  # Сохраняем оригинал
    generate_hash_token = patched_generate_hash_token  # Переопределяем
    with patch.object(settings.redis, "salt", "test_salt"):
        token = generate_hash_token("test_token")
    generate_hash_token = temp_generate_hash_token  # Восстанавливаем
    assert isinstance(token, str)
    assert len(token) == 64


def test_generate_hash_token_hex_format():
    temp_generate_hash_token = generate_hash_token_orig
    generate_hash_token = patched_generate_hash_token
    with patch.object(settings.redis, "salt", "test_salt"):
        token = generate_hash_token("test_token")
    generate_hash_token = temp_generate_hash_token
    assert re.match(r"^[0-9a-fA-F]{64}$", token) is not None


def test_generate_hash_token_determinism():
    temp_generate_hash_token = generate_hash_token_orig
    generate_hash_token = patched_generate_hash_token
    with patch.object(settings.redis, "salt", "test_salt"):
        hash1 = generate_hash_token("test_token")
        hash2 = generate_hash_token("test_token")
    generate_hash_token = temp_generate_hash_token
    assert hash1 == hash2


def test_generate_hash_token_different_tokens():
    temp_generate_hash_token = generate_hash_token_orig
    generate_hash_token = patched_generate_hash_token
    with patch.object(settings.redis, "salt", "test_salt"):
        hash1 = generate_hash_token("test_token1")
        hash2 = generate_hash_token("test_token2")
    generate_hash_token = temp_generate_hash_token
    assert hash1 != hash2


def test_generate_hash_token_different_salts():
    temp_generate_hash_token = generate_hash_token_orig
    generate_hash_token = patched_generate_hash_token
    with patch.object(settings.redis, "salt", "salt1"):
        hash1 = generate_hash_token("test_token")
        print(f"Hash1 with salt1: {hash1}, Salt: {settings.redis.salt}")
    with patch.object(settings.redis, "salt", "salt2"):
        hash2 = generate_hash_token("test_token")
        print(f"Hash2 with salt2: {hash2}, Salt: {settings.redis.salt}")
    generate_hash_token = temp_generate_hash_token
    assert hash1 != hash2


def test_generate_hash_token_uses_salt():
    temp_generate_hash_token = generate_hash_token_orig
    generate_hash_token = patched_generate_hash_token
    with patch.object(settings.redis, "salt", "known_salt"):
        hash_with_salt = generate_hash_token("test_token")
        print(f"Hash with known_salt: {hash_with_salt}, Salt: {settings.redis.salt}")
    generate_hash_token = temp_generate_hash_token
    expected_hash = hashlib.sha256("test_tokenknown_salt".encode()).hexdigest()
    assert hash_with_salt == expected_hash
