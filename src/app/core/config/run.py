from pydantic import BaseModel


class RunConfig(BaseModel):
    host: str
    port: int
