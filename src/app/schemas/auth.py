from .base import BaseSchema


class Token(BaseSchema):
    access_token: str
    refresh_token: str | None = None
    token_type: str = "Bearer"


class RefreshTokenSchema(BaseSchema):
    user_id: int
    refresh_token: str
    expires_at: str
    created_at: str
