from pydantic import EmailStr

from .base import BaseSchema


class Token(BaseSchema):
    access_token: str
    refresh_token: str
    token_type: str


class TokenPayload(BaseSchema):
    sub: EmailStr
    exp: int
