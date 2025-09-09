from pydantic import AmqpDsn, BaseModel


class TaskiqConfig(BaseModel):
    url: AmqpDsn
