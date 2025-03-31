import hashlib
from secrets import token_hex, token_urlsafe

from core.config import settings


def generate_csrf_token() -> str:
    """
    Generates a random string of 32 hexadecimal digits to be used as a CSRF token.

    :return: A string of 32 hexadecimal digits.
    """
    return token_hex(32)


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
