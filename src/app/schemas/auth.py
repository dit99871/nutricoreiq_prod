from .base import BaseSchema


class Token(BaseSchema):
    access_token: str
    refresh_token: str | None = None
    token_type: str = "Bearer"
