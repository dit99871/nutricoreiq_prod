from pydantic import BaseModel


class CacheConfig(BaseModel):
    user_ttl: int
    consent_ttl: int = 3600
