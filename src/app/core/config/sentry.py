from pydantic import BaseModel


class SentryConfig(BaseModel):
    dsn: str | None = None
