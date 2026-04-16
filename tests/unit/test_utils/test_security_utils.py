"""
Тесты для утилит безопасности.
"""

import pytest

from src.app.core.utils.security import (
    generate_csrf_token,
    generate_csp_nonce,
    generate_hash_token,
    generate_redis_session_id,
    mask_email,
)


# --- generate_csrf_token ---


def test_generate_csrf_token():
    """Тест генерации CSRF токена."""
    token = generate_csrf_token()
    
    assert isinstance(token, str)
    assert len(token) == 64  # 32 hex chars = 64 characters


def test_generate_csrf_token_different():
    """Тест что два вызова генерируют разные токены."""
    token1 = generate_csrf_token()
    token2 = generate_csrf_token()
    
    assert token1 != token2


# --- generate_redis_session_id ---


def test_generate_redis_session_id():
    """Тест генерации ID сессии Redis."""
    session_id = generate_redis_session_id()
    
    assert isinstance(session_id, str)
    assert len(session_id) == 32  # 16 hex chars = 32 characters


def test_generate_redis_session_id_different():
    """Тест что два вызова генерируют разные ID."""
    session_id1 = generate_redis_session_id()
    session_id2 = generate_redis_session_id()
    
    assert session_id1 != session_id2


# --- mask_email ---


def test_mask_email_normal():
    """Тест маскирования обычного email."""
    email = "test@example.com"
    masked = mask_email(email)
    
    assert masked == "t***t@example.com"


def test_mask_email_short_local():
    """Тест маскирования email с коротким local part (1 символ)."""
    email = "a@example.com"
    masked = mask_email(email)
    
    assert masked == "a***@example.com"


def test_mask_email_two_char_local():
    """Тест маскирования email с local part из 2 символов."""
    email = "ab@example.com"
    masked = mask_email(email)
    
    assert masked == "a***b@example.com"


def test_mask_email_empty_local():
    """Тест маскирования email с пустым local part."""
    email = "@example.com"
    masked = mask_email(email)
    
    assert masked == "***@example.com"


def test_mask_email_none():
    """Тест маскирования None."""
    masked = mask_email(None)
    
    assert masked == "<empty>"


def test_mask_email_empty_string():
    """Тест маскирования пустой строки."""
    masked = mask_email("")
    
    assert masked == "<empty>"


def test_mask_email_whitespace():
    """Тест маскирования email с пробелами."""
    email = "  test@example.com  "
    masked = mask_email(email)
    
    assert masked == "t***t@example.com"


def test_mask_email_no_at_sign():
    """Тест маскирования email без знака @."""
    email = "notanemail"
    masked = mask_email(email)
    
    assert masked == "***"


def test_mask_email_long_local():
    """Тест маскирования email с длинным local part."""
    email = "verylongusername@example.com"
    masked = mask_email(email)
    
    assert masked == "v***e@example.com"


# --- generate_csp_nonce ---


def test_generate_csp_nonce():
    """Тест генерации CSP nonce."""
    nonce = generate_csp_nonce()
    
    assert isinstance(nonce, str)
    assert len(nonce) > 0


def test_generate_csp_nonce_different():
    """Тест что два вызова генерируют разные nonce."""
    nonce1 = generate_csp_nonce()
    nonce2 = generate_csp_nonce()
    
    assert nonce1 != nonce2


def test_generate_csp_nonce_url_safe():
    """Тест что nonce URL-безопасный (без спецсимволов)."""
    nonce = generate_csp_nonce()
    
    # nonce должен содержать только URL-безопасные символы
    # (алфавитно-цифровые, -, _)
    assert all(c.isalnum() or c in '-_' for c in nonce)


# --- generate_hash_token ---


def test_generate_hash_token():
    """Тест генерации хеш-токена."""
    token = "test_token"
    hashed = generate_hash_token(token)
    
    assert isinstance(hashed, str)
    assert len(hashed) == 64  # SHA256 produces 64 hex chars


def test_generate_hash_token_deterministic():
    """Тест что хеш детерминированный для одного токена."""
    token = "test_token"
    hashed1 = generate_hash_token(token)
    hashed2 = generate_hash_token(token)
    
    assert hashed1 == hashed2


def test_generate_hash_token_different_tokens():
    """Тест что разные токены дают разные хеши."""
    hashed1 = generate_hash_token("token1")
    hashed2 = generate_hash_token("token2")
    
    assert hashed1 != hashed2


def test_generate_hash_token_empty_string():
    """Тест хеширования пустой строки."""
    hashed = generate_hash_token("")
    
    assert isinstance(hashed, str)
    assert len(hashed) == 64


def test_generate_hash_token_special_chars():
    """Тест хеширования токена со спецсимволами."""
    token = "test!@#$%^&*()"
    hashed = generate_hash_token(token)
    
    assert isinstance(hashed, str)
    assert len(hashed) == 64
