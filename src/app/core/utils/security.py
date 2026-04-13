"""Утилиты безопасности (CSRF/nonce/хеширование/маскирование)."""

import hashlib
from secrets import token_hex, token_urlsafe

from src.app.core.config import settings


def generate_csrf_token() -> str:
    """
    Генерирует случайную строку из 32 шестнадцатеричных символов для использования в качестве CSRF токена.

    :return: Строка из 32 шестнадцатеричных символов.
    """

    return token_hex(32)


def generate_redis_session_id() -> str:
    """
    Генерирует случайную шестнадцатеричную строку из 16 символов для использования в качестве ID сессии Redis.

    :return: Строка из 16 шестнадцатеричных символов.
    """

    return token_hex(16)


def mask_email(email: str | None) -> str:
    """Маскирует email для безопасного логирования."""

    if not email:
        return "<empty>"

    email = email.strip()
    if "@" not in email:
        return "***"

    local, domain = email.split("@", 1)
    if not local:
        masked_local = "***"
    elif len(local) == 1:
        masked_local = local + "***"
    elif len(local) == 2:
        masked_local = local[0] + "***" + local[-1]
    else:
        masked_local = local[0] + "***" + local[-1]

    return f"{masked_local}@{domain}"


def generate_csp_nonce() -> str:
    """
    Генерирует случайную URL-безопасную строку из 32 символов для использования в качестве nonce
    для Content Security Policy (CSP).

    :return: URL-безопасная строка из 32 символов.
    """

    return token_urlsafe(32)


def generate_hash_token(token: str) -> str:
    """
    Генерирует хеш-токен из заданного токена с добавлением соли.

    Эта функция принимает заданный токен, добавляет к нему соль из конфигурации.
    Соленый токен затем хешируется с использованием SHA256 и возвращается в виде шестнадцатеричной строки.

    :param token: Токен для добавления соли и хеширования.
    :return: Хешированный токен в виде шестнадцатеричной строки.
    """

    salted = f"{token}{settings.redis.salt}"
    return hashlib.sha256(salted.encode()).hexdigest()
