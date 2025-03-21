from datetime import datetime, timedelta
from typing import Optional

import bcrypt
from fastapi import status
from fastapi.exceptions import HTTPException
from jose import jwt, JWTError, ExpiredSignatureError

from core.config import settings
from core.logger import get_logger

log = get_logger(__name__)


def get_password_hash(password: str) -> bytes:
    salt = bcrypt.gensalt()
    pwd_bytes: bytes = password.encode()
    return bcrypt.hashpw(pwd_bytes, salt)


def verify_password(password: str, hashed_password: bytes) -> bool:
    return bcrypt.checkpw(
        password=password.encode(),
        hashed_password=hashed_password,
    )


def create_jwt(payload: dict, expires_delta: timedelta) -> str:
    try:
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
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


def decode_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(
            token,
            settings.auth.public_key_path.read_text(),
            algorithms=settings.auth.algorithm,
        )
        return payload
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File not found {str(e)}",
        )
    except ExpiredSignatureError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token has expired: {str(e)}.",
        )
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"JWT error decoding token: {str(e)}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error decoding token: {str(e)}",
        )
