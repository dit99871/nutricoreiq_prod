from datetime import datetime, timedelta
from typing import Optional

import bcrypt
from jose import jwt, JWTError

from core import settings


def get_password_hash(password: str) -> bytes:
    salt = bcrypt.gensalt()
    pwd_bytes: bytes = password.encode()
    return bcrypt.hashpw(pwd_bytes, salt)


def verify_password(password: str, hashed_password: bytes) -> bool:
    return bcrypt.checkpw(
        password=password.encode(),
        hashed_password=hashed_password,
    )


def create_token(payload: dict, expires_delta: timedelta) -> str:
    to_encode = payload.copy()
    now = datetime.utcnow()
    expire = datetime.utcnow() + expires_delta
    to_encode.update(
        {
            "exp": expire,
            "iat": now,
        }
    )
    encoded_jwt = jwt.encode(
        to_encode,
        settings.auth.private_key_path.read_text(),
        algorithm=settings.auth.algorithm,
    )
    return encoded_jwt


def decode_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(
            token,
            settings.auth.public_key_path.read_text(),
            algorithms=settings.auth.algorithm,
        )
        return payload
    except JWTError:
        return None
