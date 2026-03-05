import hashlib
from secrets import token_hex, token_urlsafe

from src.app.core.config import settings


def generate_csrf_token() -> str:
    """
    Generates a random string of 32 hexadecimal digits to be used as a CSRF token.

    :return: A string of 32 hexadecimal digits.
    """

    return token_hex(32)


def generate_redis_session_id() -> str:
    """
    Generates a random hexadecimal string of 16 characters to be used as a Redis session ID.

    :return: A string of 16 hexadecimal characters.
    """

    return token_hex(16)


def mask_email(email: str | None) -> str:
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
    Generates a random URL-safe string of 32 characters to be used as a nonce
    for Content Security Policy (CSP).

    :return: A URL-safe string of 32 characters.
    """

    return token_urlsafe(32)


def generate_hash_token(token: str) -> str:
    """
    Generates a hash token from given token with added salt.

    This function takes a given token and adds a salt to it from the configuration.
    The salted token is then hashed using SHA256 and returned as a hexadecimal string.

    :param token: The token to be salted and hashed.
    :return: The hashed token as a hexadecimal string.
    """

    salted = f"{token}{settings.redis.salt}"
    return hashlib.sha256(salted.encode()).hexdigest()
