from pydantic import BaseModel


class RouterPrefix(BaseModel):
    auth: str = "/auth"
    product: str = "/product"
    user: str = "/user"
    security: str = "/security"
