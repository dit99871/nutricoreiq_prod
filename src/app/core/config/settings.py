from pydantic import PostgresDsn
from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict,
)

from src.app.core.constants import BASE_DIR
from .auth import AuthConfig
from .cors import CORSConfig
from .db import DatabaseConfig
from .env import EnvConfig
from .logging import LoggingConfig
from .loki import LokiConfig
from .redis import RedisConfig
from .routers_prefixs import RouterPrefix
from .run import RunConfig
from .sentry import SentyConfig
from .smtp import SMTPConfig
from .taskiq import TaskiqConfig

class Settings(BaseSettings):
    DEBUG: bool = False

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        case_sensitive=False,
        env_nested_delimiter="__",
        env_prefix="APP_CONFIG__",
    )

    env: EnvConfig
    run: RunConfig
    logging: LoggingConfig = LoggingConfig()
    router: RouterPrefix = RouterPrefix()
    db: DatabaseConfig
    auth: AuthConfig
    redis: RedisConfig
    cors: CORSConfig
    mail: SMTPConfig
    taskiq: TaskiqConfig
    sentry: SentyConfig
    loki: LokiConfig

    @property
    def effective_db_url(self) -> PostgresDsn:
        if self.db.is_test and self.db.test_url:
            return self.db.test_url
        if self.db.url:
            return self.db.url
        raise ValueError("Neither db.url nor db.test_url is provided when needed.")


settings = Settings()
