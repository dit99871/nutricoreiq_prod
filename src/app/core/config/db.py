from typing import Optional

from pydantic import BaseModel, PostgresDsn


class DatabaseConfig(BaseModel):
    url: Optional[PostgresDsn] = None
    echo: bool = False
    is_test: bool = False
    test_url: Optional[PostgresDsn] = None
    test_echo: Optional[bool] = None
    echo_pool: bool = False
    pool_size: int = 5
    max_overflow: int = 10

    naming_convention: dict[str, str] = {
        "ix": "ix_%(column_0_label)s",
        "uq": "uq_%(table_name)s_%(column_0_N_name)s",
        "ck": "ck_%(table_name)s_%(constraint_name)s",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s",
    }
