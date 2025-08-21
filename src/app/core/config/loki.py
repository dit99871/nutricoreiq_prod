from pydantic import BaseModel


class LokiConfig(BaseModel):
    url: str
