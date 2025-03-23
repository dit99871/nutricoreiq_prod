from pydantic import BaseModel, ConfigDict


class BaseSchema(BaseModel):
    id: int

    model_config = ConfigDict(
        from_attributes=True,
    )
