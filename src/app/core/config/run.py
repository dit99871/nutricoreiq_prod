from pydantic import BaseModel


class RunConfig(BaseModel):
    host: str
    port: int
    trusted_proxies: list[str] = []
