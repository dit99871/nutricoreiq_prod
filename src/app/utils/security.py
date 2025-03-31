import hashlib
from secrets import token_hex, token_urlsafe

from core.config import settings


def generate_csrf_token() -> str:
    return token_hex(32)


def generate_csp_nonce() -> str:
    return token_urlsafe(32)


def generate_hash_token(token: str) -> str:
    salted = f"{token}{settings.redis.salt}"
    return hashlib.sha256(salted.encode()).hexdigest()
