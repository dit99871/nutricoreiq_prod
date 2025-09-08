from pydantic import BaseModel


class CacheConfig(BaseModel):
    user_ttl: int
