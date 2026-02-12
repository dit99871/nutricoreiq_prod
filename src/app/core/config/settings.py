from pydantic import PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict

from src.app.core.constants import BASE_DIR

from .auth import AuthConfig
from .cache import CacheConfig
from .cors import CORSConfig
from .db import DatabaseConfig
from .env import EnvConfig
from .logging import LoggingConfig
from .loki import LokiConfig
from .rate_limit import RateLimitConfig
from .redis import RedisConfig
from .routers_prefixs import RouterPrefix
from .run import RunConfig
from .sentry import SentyConfig
from .smtp import SMTPConfig
from .taskiq import TaskiqConfig


class Settings(BaseSettings):
    DEBUG: bool = False

    # переменные для Docker Compose (без префикса)
    POSTGRES_DB: str = ""
    POSTGRES_USER: str = ""
    POSTGRES_PASSWORD: str = ""
    POSTGRES_HOST: str = ""
    POSTGRES_PORT: str = ""
    POSTGRES_SSL_MODE: str = ""
    REDIS_PORT: str = ""
    REDIS_ADDR: str = ""
    REDIS_LOG_LEVEL: str = ""
    HTTP_PORT: str = ""
    HTTPS_PORT: str = ""
    GF_SERVER_PROTOCOL: str = ""
    GF_SERVER_DOMAIN: str = ""
    GF_SERVER_ROOT_URL: str = ""
    RABBITMQ_PORT: str = ""
    RABBITMQ_MANAGEMENT_PORT: str = ""
    RABBITMQ_DEFAULT_USER: str = ""
    RABBITMQ_DEFAULT_PASS: str = ""

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        case_sensitive=False,
        env_nested_delimiter="__",
        env_prefix="APP_CONFIG__",
        extra="ignore",
    )

    auth: AuthConfig
    cache: CacheConfig
    cors: CORSConfig
    db: DatabaseConfig
    env: EnvConfig
    mail: SMTPConfig
    redis: RedisConfig
    run: RunConfig
    taskiq: TaskiqConfig

    logging: LoggingConfig = LoggingConfig()
    loki: LokiConfig = LokiConfig()
    rate_limit: RateLimitConfig = RateLimitConfig()
    router: RouterPrefix = RouterPrefix()
    sentry: SentyConfig = SentyConfig()

    @property
    def effective_db_url(self) -> PostgresDsn:
        if self.env.env == "test" and self.db.test_url:
            return self.db.test_url
        if self.db.url:
            return self.db.url
        raise ValueError("Neither db.url nor db.test_url is provided when needed.")


settings = Settings()
