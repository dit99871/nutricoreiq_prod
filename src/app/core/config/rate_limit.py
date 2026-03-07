from pydantic import BaseModel


class RateLimitConfig(BaseModel):
    register_limit: str = "5/minute"
    login_limit: str = "5/minute"
    password_change_limit: str = "3/minute"
    storage_uri: str | None = None  # переопределяет redis.url
