"""
Тесты для моделей конфигурации приложения.
Проверяют валидацию, значения по умолчанию и граничные случаи
для каждого sub-config класса без необходимости реального .env файла.
"""

import pytest
from pydantic import ValidationError


# ─── AuthConfig ──────────────────────────────────────────────────────────────


class TestAuthConfig:
    """Тесты для AuthConfig."""

    def test_auth_config_valid(self):
        from src.app.core.config.auth import AuthConfig

        cfg = AuthConfig(algorithm="RS256", access_token_expires=15, refresh_token_expires=30)
        assert cfg.algorithm == "RS256"
        assert cfg.access_token_expires == 15
        assert cfg.refresh_token_expires == 30

    def test_auth_config_missing_algorithm(self):
        from src.app.core.config.auth import AuthConfig

        with pytest.raises(ValidationError):
            AuthConfig(access_token_expires=15, refresh_token_expires=30)

    def test_auth_config_default_key_paths(self):
        from pathlib import Path

        from src.app.core.config.auth import AuthConfig

        cfg = AuthConfig(algorithm="HS256", access_token_expires=10, refresh_token_expires=20)
        assert isinstance(cfg.private_key_path, Path)
        assert isinstance(cfg.public_key_path, Path)
        assert "jwt-private.pem" in str(cfg.private_key_path)
        assert "jwt-public.pem" in str(cfg.public_key_path)

    def test_auth_config_custom_key_paths(self, tmp_path):
        from src.app.core.config.auth import AuthConfig

        private = tmp_path / "private.pem"
        public = tmp_path / "public.pem"
        cfg = AuthConfig(
            algorithm="RS256",
            access_token_expires=60,
            refresh_token_expires=86400,
            private_key_path=private,
            public_key_path=public,
        )
        assert cfg.private_key_path == private
        assert cfg.public_key_path == public


# ─── CacheConfig ─────────────────────────────────────────────────────────────


class TestCacheConfig:
    """Тесты для CacheConfig."""

    def test_cache_config_valid(self):
        from src.app.core.config.cache import CacheConfig

        cfg = CacheConfig(user_ttl=3600)
        assert cfg.user_ttl == 3600

    def test_cache_config_default_consent_ttl(self):
        from src.app.core.config.cache import CacheConfig

        cfg = CacheConfig(user_ttl=100)
        assert cfg.consent_ttl == 3600

    def test_cache_config_custom_consent_ttl(self):
        from src.app.core.config.cache import CacheConfig

        cfg = CacheConfig(user_ttl=100, consent_ttl=7200)
        assert cfg.consent_ttl == 7200

    def test_cache_config_missing_user_ttl(self):
        from src.app.core.config.cache import CacheConfig

        with pytest.raises(ValidationError):
            CacheConfig()


# ─── CORSConfig ──────────────────────────────────────────────────────────────


class TestCORSConfig:
    """Тесты для CORSConfig."""

    def test_cors_config_valid(self):
        from src.app.core.config.cors import CORSConfig

        cfg = CORSConfig(
            allow_origins=["http://localhost"],
            allow_methods=["GET", "POST"],
            allow_headers=["*"],
            allow_credentials=True,
        )
        assert cfg.allow_credentials is True
        assert "GET" in cfg.allow_methods

    def test_cors_config_empty_origins(self):
        from src.app.core.config.cors import CORSConfig

        cfg = CORSConfig(
            allow_origins=[],
            allow_methods=["GET"],
            allow_headers=["Content-Type"],
            allow_credentials=False,
        )
        assert cfg.allow_origins == []

    def test_cors_config_missing_field(self):
        from src.app.core.config.cors import CORSConfig

        with pytest.raises(ValidationError):
            CORSConfig(allow_origins=["http://localhost"])


# ─── DatabaseConfig ──────────────────────────────────────────────────────────


class TestDatabaseConfig:
    """Тесты для DatabaseConfig."""

    def test_db_config_defaults(self):
        from src.app.core.config.db import DatabaseConfig

        cfg = DatabaseConfig()
        assert cfg.echo is False
        assert cfg.is_test is False
        assert cfg.pool_size == 5
        assert cfg.max_overflow == 10
        assert cfg.url is None
        assert cfg.test_url is None

    def test_db_config_with_url(self):
        from src.app.core.config.db import DatabaseConfig

        cfg = DatabaseConfig(url="postgresql+asyncpg://user:pass@localhost/mydb")
        assert cfg.url is not None

    def test_db_config_naming_convention_keys(self):
        from src.app.core.config.db import DatabaseConfig

        cfg = DatabaseConfig()
        assert "ix" in cfg.naming_convention
        assert "uq" in cfg.naming_convention
        assert "fk" in cfg.naming_convention
        assert "pk" in cfg.naming_convention

    def test_db_config_custom_pool(self):
        from src.app.core.config.db import DatabaseConfig

        cfg = DatabaseConfig(pool_size=10, max_overflow=20, echo=True)
        assert cfg.pool_size == 10
        assert cfg.max_overflow == 20
        assert cfg.echo is True


# ─── EnvConfig ───────────────────────────────────────────────────────────────


class TestEnvConfig:
    """Тесты для EnvConfig."""

    def test_env_config_default(self):
        from src.app.core.config.env import EnvConfig

        cfg = EnvConfig()
        assert cfg.env == "dev"

    def test_env_config_prod(self):
        from src.app.core.config.env import EnvConfig

        cfg = EnvConfig(env="prod")
        assert cfg.env == "prod"

    def test_env_config_test(self):
        from src.app.core.config.env import EnvConfig

        cfg = EnvConfig(env="test")
        assert cfg.env == "test"


# ─── SMTPConfig ──────────────────────────────────────────────────────────────


class TestSMTPConfig:
    """Тесты для SMTPConfig."""

    def test_smtp_config_minimal(self):
        from src.app.core.config.smtp import SMTPConfig

        cfg = SMTPConfig(
            host="smtp.example.com",
            port=587,
            button_link="http://example.com",
            unsubscribe_link="http://example.com/unsub",
        )
        assert cfg.host == "smtp.example.com"
        assert cfg.port == 587
        assert cfg.username is None
        assert cfg.password is None
        assert cfg.use_tls is None

    def test_smtp_config_with_auth(self):
        from src.app.core.config.smtp import SMTPConfig

        cfg = SMTPConfig(
            host="smtp.example.com",
            port=465,
            button_link="http://example.com",
            unsubscribe_link="http://example.com/unsub",
            username="user@example.com",
            password="secret",
            use_tls=True,
        )
        assert cfg.username == "user@example.com"
        assert cfg.use_tls is True

    def test_smtp_config_missing_required(self):
        from src.app.core.config.smtp import SMTPConfig

        with pytest.raises(ValidationError):
            SMTPConfig(host="smtp.example.com")


# ─── RedisConfig ─────────────────────────────────────────────────────────────


class TestRedisConfig:
    """Тесты для RedisConfig."""

    def test_redis_config_valid(self):
        from src.app.core.config.redis import RedisConfig

        cfg = RedisConfig(
            url="redis://localhost:6379",
            salt="mysalt",
            password="secret",
            session_ttl=3600,
        )
        assert cfg.url == "redis://localhost:6379"
        assert cfg.salt == "mysalt"
        assert cfg.session_ttl == 3600

    def test_redis_config_missing_fields(self):
        from src.app.core.config.redis import RedisConfig

        with pytest.raises(ValidationError):
            RedisConfig()


# ─── RunConfig ───────────────────────────────────────────────────────────────


class TestRunConfig:
    """Тесты для RunConfig."""

    def test_run_config_valid(self):
        from src.app.core.config.run import RunConfig

        cfg = RunConfig(host="0.0.0.0", port=8000)
        assert cfg.host == "0.0.0.0"
        assert cfg.port == 8000
        assert cfg.trusted_proxies == []

    def test_run_config_with_proxies(self):
        from src.app.core.config.run import RunConfig

        cfg = RunConfig(host="127.0.0.1", port=8080, trusted_proxies=["10.0.0.1", "172.16.0.0/12"])
        assert len(cfg.trusted_proxies) == 2


# ─── LoggingConfig ───────────────────────────────────────────────────────────


class TestLoggingConfig:
    """Тесты для LoggingConfig."""

    def test_logging_config_defaults(self):
        from src.app.core.config.logging import LoggingConfig

        cfg = LoggingConfig()
        assert cfg.log_level == "INFO"
        assert cfg.log_interval == 1
        assert cfg.log_file_backup_count == 7
        assert cfg.log_utc is True

    def test_logging_config_log_level_value(self):
        import logging

        from src.app.core.config.logging import LoggingConfig

        cfg = LoggingConfig(log_level="DEBUG")
        assert cfg.log_level_value == logging.DEBUG

    def test_logging_config_all_levels(self):
        import logging

        from src.app.core.config.logging import LoggingConfig

        levels = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL,
        }
        for level_name, level_value in levels.items():
            cfg = LoggingConfig(log_level=level_name)
            assert cfg.log_level_value == level_value

    def test_logging_config_invalid_level(self):
        from src.app.core.config.logging import LoggingConfig

        with pytest.raises(ValidationError):
            LoggingConfig(log_level="TRACE")

    def test_logging_config_custom_format(self):
        from src.app.core.config.logging import LoggingConfig

        custom_fmt = "%(levelname)s - %(message)s"
        cfg = LoggingConfig(log_format=custom_fmt)
        assert cfg.log_format == custom_fmt


# ─── RateLimitConfig ─────────────────────────────────────────────────────────


class TestRateLimitConfig:
    """Тесты для RateLimitConfig."""

    def test_rate_limit_config_defaults(self):
        from src.app.core.config.rate_limit import RateLimitConfig

        cfg = RateLimitConfig()
        # просто проверяем что создается без ошибок
        assert cfg is not None


# ─── RouterPrefix ────────────────────────────────────────────────────────────


class TestRouterPrefix:
    """Тесты для RouterPrefix."""

    def test_router_prefix_defaults(self):
        from src.app.core.config.routers_prefixs import RouterPrefix

        cfg = RouterPrefix()
        assert cfg is not None


# ─── TaskiqConfig ─────────────────────────────────────────────────────────────


class TestTaskiqConfig:
    """Тесты для TaskiqConfig."""

    def test_taskiq_config_valid(self):
        from src.app.core.config.taskiq import TaskiqConfig

        cfg = TaskiqConfig(url="amqp://guest:guest@localhost/")
        assert "amqp" in str(cfg.url)

    def test_taskiq_config_missing_url(self):
        from src.app.core.config.taskiq import TaskiqConfig

        with pytest.raises(ValidationError):
            TaskiqConfig()