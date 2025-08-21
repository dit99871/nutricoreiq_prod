from pydantic import BaseModel


class RedisConfig(BaseModel):
    url: str
    salt: str
    password: str
    session_ttl: int
