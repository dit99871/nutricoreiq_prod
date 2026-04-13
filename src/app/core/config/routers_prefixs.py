"""Префиксы для API-роутеров."""

from pydantic import BaseModel


class RouterPrefix(BaseModel):
    """Пути-префиксы для основных групп роутов."""

    auth: str = "/auth"
    product: str = "/product"
    user: str = "/user"
    security: str = "/security"
    privacy: str = "/privacy"
