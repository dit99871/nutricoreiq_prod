"""
Тесты для DatabaseHelper и вспомогательных функций работы с БД.
Покрывает: DatabaseHelper.__init__, dispose, session_getter.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ─── DatabaseHelper ──────────────────────────────────────────────────────────


class TestDatabaseHelper:
    """Тесты для класса DatabaseHelper."""

    def _make_helper(self, url="postgresql+asyncpg://user:pass@localhost/testdb", **kwargs):
        """Создаёт DatabaseHelper с замоканным SQLAlchemy."""
        with patch("src.app.core.db_helper.create_async_engine") as mock_engine:
            with patch("src.app.core.db_helper.async_sessionmaker") as mock_factory:
                mock_engine.return_value = MagicMock()
                mock_factory.return_value = MagicMock()
                from src.app.core.db_helper import DatabaseHelper
                helper = DatabaseHelper(url=url, **kwargs)
                return helper, mock_engine, mock_factory

    def test_init_creates_engine(self):
        """__init__ создаёт async engine с переданным URL."""
        with patch("src.app.core.db_helper.create_async_engine") as mock_engine:
            with patch("src.app.core.db_helper.async_sessionmaker"):
                mock_engine.return_value = MagicMock()
                from src.app.core.db_helper import DatabaseHelper

                DatabaseHelper(url="postgresql+asyncpg://user:pass@localhost/db")

        mock_engine.assert_called_once()
        call_kwargs = mock_engine.call_args[1]
        assert "postgresql+asyncpg" in call_kwargs["url"]

    def test_init_passes_echo_to_engine(self):
        """Параметр echo передаётся в create_async_engine."""
        with patch("src.app.core.db_helper.create_async_engine") as mock_engine:
            with patch("src.app.core.db_helper.async_sessionmaker"):
                mock_engine.return_value = MagicMock()
                from src.app.core.db_helper import DatabaseHelper

                DatabaseHelper(url="postgresql+asyncpg://u:p@h/db", echo=True)

        call_kwargs = mock_engine.call_args[1]
        assert call_kwargs["echo"] is True

    def test_init_passes_pool_size_to_engine(self):
        """Параметры пула передаются в create_async_engine."""
        with patch("src.app.core.db_helper.create_async_engine") as mock_engine:
            with patch("src.app.core.db_helper.async_sessionmaker"):
                mock_engine.return_value = MagicMock()
                from src.app.core.db_helper import DatabaseHelper

                DatabaseHelper(
                    url="postgresql+asyncpg://u:p@h/db",
                    pool_size=10,
                    max_overflow=20,
                )

        call_kwargs = mock_engine.call_args[1]
        assert call_kwargs["pool_size"] == 10
        assert call_kwargs["max_overflow"] == 20

    def test_init_creates_session_factory(self):
        """__init__ создаёт async_sessionmaker."""
        with patch("src.app.core.db_helper.create_async_engine") as mock_engine:
            with patch("src.app.core.db_helper.async_sessionmaker") as mock_factory:
                mock_engine.return_value = MagicMock()
                from src.app.core.db_helper import DatabaseHelper

                helper = DatabaseHelper(url="postgresql+asyncpg://u:p@h/db")

        mock_factory.assert_called_once()
        assert helper.session_factory is mock_factory.return_value

    def test_session_factory_configured_correctly(self):
        """session_factory настроен с autoflush=False и autocommit=False."""
        with patch("src.app.core.db_helper.create_async_engine") as mock_engine:
            with patch("src.app.core.db_helper.async_sessionmaker") as mock_factory:
                mock_engine.return_value = MagicMock()
                from src.app.core.db_helper import DatabaseHelper

                DatabaseHelper(url="postgresql+asyncpg://u:p@h/db")

        call_kwargs = mock_factory.call_args[1]
        assert call_kwargs["autoflush"] is False
        assert call_kwargs["autocommit"] is False
        assert call_kwargs["expire_on_commit"] is False

    @pytest.mark.asyncio
    async def test_dispose_calls_engine_dispose(self):
        """dispose() вызывает engine.dispose()."""
        with patch("src.app.core.db_helper.create_async_engine") as mock_engine_fn:
            with patch("src.app.core.db_helper.async_sessionmaker"):
                mock_engine = MagicMock()
                mock_engine.dispose = AsyncMock()
                mock_engine_fn.return_value = mock_engine

                from src.app.core.db_helper import DatabaseHelper

                helper = DatabaseHelper(url="postgresql+asyncpg://u:p@h/db")
                await helper.dispose()

        mock_engine.dispose.assert_called_once()

    @pytest.mark.asyncio
    async def test_session_getter_yields_session(self):
        """session_getter — генератор, выдающий AsyncSession."""
        mock_session = AsyncMock()
        mock_cm = AsyncMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_session)
        mock_cm.__aexit__ = AsyncMock(return_value=None)

        mock_factory = MagicMock(return_value=mock_cm)

        with patch("src.app.core.db_helper.create_async_engine") as mock_engine_fn:
            with patch("src.app.core.db_helper.async_sessionmaker", return_value=mock_factory):
                mock_engine_fn.return_value = MagicMock()

                from src.app.core.db_helper import DatabaseHelper

                helper = DatabaseHelper(url="postgresql+asyncpg://u:p@h/db")
                helper.session_factory = mock_factory

                sessions = []
                async for session in helper.session_getter():
                    sessions.append(session)

        assert len(sessions) == 1
        assert sessions[0] is mock_session

    def test_default_parameters(self):
        """Параметры по умолчанию применяются корректно."""
        with patch("src.app.core.db_helper.create_async_engine") as mock_engine:
            with patch("src.app.core.db_helper.async_sessionmaker"):
                mock_engine.return_value = MagicMock()
                from src.app.core.db_helper import DatabaseHelper

                DatabaseHelper(url="postgresql+asyncpg://u:p@h/db")

        call_kwargs = mock_engine.call_args[1]
        assert call_kwargs["echo"] is False
        assert call_kwargs["echo_pool"] is False
        assert call_kwargs["pool_size"] == 5
        assert call_kwargs["max_overflow"] == 10