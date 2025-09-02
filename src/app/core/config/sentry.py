from pydantic import BaseModel


class SentyConfig(BaseModel):
    dsn: str
