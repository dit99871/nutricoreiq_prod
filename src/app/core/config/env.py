from pydantic import BaseModel


class EnvConfig(BaseModel):
    env: str = "dev"
