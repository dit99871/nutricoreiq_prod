from pydantic import BaseModel, AmqpDsn


class TaskiqConfig(BaseModel):
    url: AmqpDsn
