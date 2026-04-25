"""
Тесты для сервиса Sentry (sentry_service.py).
Покрывает: sentry_to_loki, init_sentry.

В синхронном тест-контексте asyncio.get_running_loop() всегда поднимает
RuntimeError (нет event loop) → срабатывает ветка log.warning.
Для теста success-пути используем async-тест.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ─── sentry_to_loki ──────────────────────────────────────────────────────────


class TestSentryToLoki:

    def test_returns_event_unchanged(self):
        from src.app.core.services.sentry import sentry_to_loki
        event = {"event_id": "abc", "message": "Test error", "level": "error"}
        with patch("src.app.core.services.sentry.log"):
            result = sentry_to_loki(event, hint=None)
        assert result is event

    def test_no_loop_logs_warning(self):
        """В sync-контексте нет loop → RuntimeError → warning."""
        from src.app.core.services.sentry import sentry_to_loki
        event = {"event_id": "xyz", "message": "No loop", "level": "error"}
        with patch("src.app.core.services.sentry.log") as mock_log:
            sentry_to_loki(event, hint=None)
        mock_log.warning.assert_called_once()
        mock_log.error.assert_not_called()

    def test_no_loop_returns_event(self):
        from src.app.core.services.sentry import sentry_to_loki
        event = {"event_id": "xyz2", "message": "No loop", "level": "error"}
        with patch("src.app.core.services.sentry.log"):
            result = sentry_to_loki(event, hint=None)
        assert result is event

    def test_unexpected_exception_logs_error(self):
        """Ошибка не RuntimeError → log.error."""
        from src.app.core.services.sentry import sentry_to_loki
        event = {"event_id": "err", "message": "Boom", "level": "fatal"}
        with patch("src.app.core.services.sentry.asyncio") as mock_asyncio:
            mock_asyncio.get_running_loop.side_effect = TypeError("oops")
            with patch("src.app.core.services.sentry.log") as mock_log:
                result = sentry_to_loki(event, hint=None)
        assert result is event
        mock_log.error.assert_called_once()

    def test_unexpected_exception_returns_event(self):
        from src.app.core.services.sentry import sentry_to_loki
        event = {"event_id": "any", "message": "test", "level": "error"}
        with patch("src.app.core.services.sentry.asyncio") as mock_asyncio:
            mock_asyncio.get_running_loop.side_effect = OSError("OS error")
            with patch("src.app.core.services.sentry.log"):
                result = sentry_to_loki(event, hint=None)
        assert result is event

    @pytest.mark.asyncio
    async def test_creates_task_when_loop_running(self):
        """В async-контексте есть loop → create_task вызывается."""
        import asyncio
        from src.app.core.services.sentry import sentry_to_loki

        event = {"event_id": "loop-ok", "message": "Test", "level": "info"}
        tasks_created = []

        loop = asyncio.get_event_loop()

        def capture_task(coro):
            coro.close()
            t = MagicMock()
            tasks_created.append(t)
            return t

        with patch("src.app.core.tasks.send_event_to_loki") as mock_send:
            mock_send.kiq = AsyncMock(return_value=None)
            with patch("src.app.core.services.sentry.log") as mock_log:
                with patch.object(loop, "create_task", side_effect=capture_task):
                    result = sentry_to_loki(event, hint=None)

        assert result is event
        assert len(tasks_created) == 1
        mock_log.info.assert_called_once()

    def test_missing_message_key_handled(self):
        from src.app.core.services.sentry import sentry_to_loki
        event = {"event_id": "no-msg", "level": "error"}
        with patch("src.app.core.services.sentry.log"):
            result = sentry_to_loki(event, hint=None)
        assert result is event

    def test_missing_level_key_handled(self):
        from src.app.core.services.sentry import sentry_to_loki
        event = {"event_id": "no-level", "message": "Some message"}
        with patch("src.app.core.services.sentry.log"):
            result = sentry_to_loki(event, hint=None)
        assert result is event

    def test_none_event_id_handled(self):
        from src.app.core.services.sentry import sentry_to_loki
        event = {"event_id": None, "message": "no id", "level": "warning"}
        with patch("src.app.core.services.sentry.log"):
            result = sentry_to_loki(event, hint=None)
        assert result is event


# ─── init_sentry ─────────────────────────────────────────────────────────────


class TestInitSentry:

    def test_no_dsn_logs_error(self):
        from src.app.core.services.sentry import init_sentry
        mock_settings = MagicMock()
        mock_settings.sentry.dsn = None
        with patch("src.app.core.services.sentry.settings", mock_settings):
            with patch("src.app.core.services.sentry.log") as mock_log:
                result = init_sentry()
        assert result is None
        mock_log.error.assert_called_once()

    def test_empty_dsn_returns_none(self):
        from src.app.core.services.sentry import init_sentry
        mock_settings = MagicMock()
        mock_settings.sentry.dsn = ""
        with patch("src.app.core.services.sentry.settings", mock_settings):
            with patch("src.app.core.services.sentry.log") as mock_log:
                result = init_sentry()
        assert result is None
        mock_log.error.assert_called_once()

    def test_no_dsn_skips_sdk_init(self):
        from src.app.core.services.sentry import init_sentry
        mock_settings = MagicMock()
        mock_settings.sentry.dsn = None
        with patch("src.app.core.services.sentry.settings", mock_settings):
            with patch("src.app.core.services.sentry.sentry_sdk") as mock_sdk:
                with patch("src.app.core.services.sentry.log"):
                    init_sentry()
        mock_sdk.init.assert_not_called()

    def test_with_dsn_calls_sdk_init(self):
        from src.app.core.services.sentry import init_sentry
        mock_settings = MagicMock()
        mock_settings.sentry.dsn = "https://key@sentry.io/123"
        with patch("src.app.core.services.sentry.settings", mock_settings):
            with patch("src.app.core.services.sentry.sentry_sdk") as mock_sdk:
                init_sentry()
        mock_sdk.init.assert_called_once()

    def test_passes_correct_dsn(self):
        from src.app.core.services.sentry import init_sentry
        dsn = "https://abc@sentry.io/456"
        mock_settings = MagicMock()
        mock_settings.sentry.dsn = dsn
        with patch("src.app.core.services.sentry.settings", mock_settings):
            with patch("src.app.core.services.sentry.sentry_sdk") as mock_sdk:
                init_sentry()
        assert mock_sdk.init.call_args[1]["dsn"] == dsn

    def test_send_default_pii_false(self):
        from src.app.core.services.sentry import init_sentry
        mock_settings = MagicMock()
        mock_settings.sentry.dsn = "https://key@sentry.io/1"
        with patch("src.app.core.services.sentry.settings", mock_settings):
            with patch("src.app.core.services.sentry.sentry_sdk") as mock_sdk:
                init_sentry()
        assert mock_sdk.init.call_args[1]["send_default_pii"] is False

    def test_before_send_is_sentry_to_loki(self):
        from src.app.core.services.sentry import init_sentry, sentry_to_loki
        mock_settings = MagicMock()
        mock_settings.sentry.dsn = "https://key@sentry.io/1"
        with patch("src.app.core.services.sentry.settings", mock_settings):
            with patch("src.app.core.services.sentry.sentry_sdk") as mock_sdk:
                init_sentry()
        assert mock_sdk.init.call_args[1]["before_send"] is sentry_to_loki