"""
Тесты для Taskiq-задачи отправки событий в Loki (sentry_task.py).
Покрывает: send_event_to_loki — успех, HTTP ошибки, сетевые ошибки.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ─── send_event_to_loki ───────────────────────────────────────────────────────


class TestSendEventToLoki:
    """Тесты для задачи send_event_to_loki."""

    @pytest.mark.asyncio
    async def test_successful_send(self):
        """Успешная отправка — не поднимает исключений."""
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        mock_settings = MagicMock()
        mock_settings.loki.url = "http://loki:3100/loki/api/v1/push"

        with patch("src.app.core.tasks.sentry_task.settings", mock_settings):
            with patch("src.app.core.tasks.sentry_task.httpx.AsyncClient", return_value=mock_client):
                with patch("src.app.core.tasks.sentry_task.log"):
                    from src.app.core.tasks.sentry_task import send_event_to_loki

                    await send_event_to_loki(
                        event_id="test-event-123",
                        message="Test error occurred",
                        level="error",
                    )

        mock_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_sends_correct_url(self):
        """POST выполняется на корректный Loki URL."""
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        loki_url = "http://loki:3100/loki/api/v1/push"
        mock_settings = MagicMock()
        mock_settings.loki.url = loki_url

        with patch("src.app.core.tasks.sentry_task.settings", mock_settings):
            with patch("src.app.core.tasks.sentry_task.httpx.AsyncClient", return_value=mock_client):
                with patch("src.app.core.tasks.sentry_task.log"):
                    from src.app.core.tasks.sentry_task import send_event_to_loki

                    await send_event_to_loki(
                        event_id="evt-1", message="msg", level="warning"
                    )

        call_args = mock_client.post.call_args
        assert call_args[0][0] == loki_url

    @pytest.mark.asyncio
    async def test_sends_valid_json_payload(self):
        """Тело запроса содержит корректную структуру Loki push."""
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()

        captured_payload = {}

        async def capture_post(url, json=None, **kwargs):
            captured_payload.update(json or {})
            return mock_response

        mock_client = AsyncMock()
        mock_client.post = capture_post
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        mock_settings = MagicMock()
        mock_settings.loki.url = "http://loki:3100/loki/api/v1/push"

        with patch("src.app.core.tasks.sentry_task.settings", mock_settings):
            with patch("src.app.core.tasks.sentry_task.httpx.AsyncClient", return_value=mock_client):
                with patch("src.app.core.tasks.sentry_task.log"):
                    from src.app.core.tasks.sentry_task import send_event_to_loki

                    await send_event_to_loki(
                        event_id="abc", message="Test message", level="error"
                    )

        assert "streams" in captured_payload
        stream = captured_payload["streams"][0]
        assert stream["stream"]["source"] == "sentry"
        assert stream["stream"]["level"] == "error"
        assert stream["stream"]["app"] == "fastapi"

    @pytest.mark.asyncio
    async def test_payload_values_contain_message_and_event_id(self):
        """values в payload содержат message и event_id."""
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()

        captured_payload = {}

        async def capture_post(url, json=None, **kwargs):
            captured_payload.update(json or {})
            return mock_response

        mock_client = AsyncMock()
        mock_client.post = capture_post
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        mock_settings = MagicMock()
        mock_settings.loki.url = "http://loki:3100/loki/api/v1/push"

        with patch("src.app.core.tasks.sentry_task.settings", mock_settings):
            with patch("src.app.core.tasks.sentry_task.httpx.AsyncClient", return_value=mock_client):
                with patch("src.app.core.tasks.sentry_task.log"):
                    from src.app.core.tasks.sentry_task import send_event_to_loki

                    await send_event_to_loki(
                        event_id="event-xyz", message="Error happened", level="error"
                    )

        values = captured_payload["streams"][0]["values"]
        assert len(values) == 1
        timestamp_ns, log_json = values[0]

        # timestamp — строка с числом
        assert timestamp_ns.isdigit()

        # log_json — валидный JSON
        log_data = json.loads(log_json)
        assert log_data["message"] == "Error happened"
        assert log_data["event_id"] == "event-xyz"
        assert "time" in log_data

    @pytest.mark.asyncio
    async def test_http_error_logs_and_reraises(self):
        """HTTP ошибка логируется и пробрасывается для retry."""
        import httpx

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=httpx.HTTPStatusError(
            "Server error",
            request=MagicMock(),
            response=MagicMock(status_code=500),
        ))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        mock_settings = MagicMock()
        mock_settings.loki.url = "http://loki:3100/loki/api/v1/push"

        with patch("src.app.core.tasks.sentry_task.settings", mock_settings):
            with patch("src.app.core.tasks.sentry_task.httpx.AsyncClient", return_value=mock_client):
                with patch("src.app.core.tasks.sentry_task.log") as mock_log:
                    from src.app.core.tasks.sentry_task import send_event_to_loki

                    with pytest.raises(Exception):
                        await send_event_to_loki(
                            event_id="fail", message="test", level="error"
                        )

                mock_log.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_connection_error_logs_and_reraises(self):
        """Сетевая ошибка логируется и пробрасывается."""
        import httpx

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        mock_settings = MagicMock()
        mock_settings.loki.url = "http://loki:3100/loki/api/v1/push"

        with patch("src.app.core.tasks.sentry_task.settings", mock_settings):
            with patch("src.app.core.tasks.sentry_task.httpx.AsyncClient", return_value=mock_client):
                with patch("src.app.core.tasks.sentry_task.log") as mock_log:
                    from src.app.core.tasks.sentry_task import send_event_to_loki

                    with pytest.raises(Exception):
                        await send_event_to_loki(
                            event_id="conn-err", message="test", level="error"
                        )

                mock_log.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_none_event_id_handled(self):
        """event_id=None не вызывает ошибок."""
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        mock_settings = MagicMock()
        mock_settings.loki.url = "http://loki:3100/loki/api/v1/push"

        with patch("src.app.core.tasks.sentry_task.settings", mock_settings):
            with patch("src.app.core.tasks.sentry_task.httpx.AsyncClient", return_value=mock_client):
                with patch("src.app.core.tasks.sentry_task.log"):
                    from src.app.core.tasks.sentry_task import send_event_to_loki

                    # не должно падать
                    await send_event_to_loki(
                        event_id=None, message="no id event", level="info"
                    )

    @pytest.mark.asyncio
    async def test_logs_success_info(self):
        """При успехе логируется info сообщение."""
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        mock_settings = MagicMock()
        mock_settings.loki.url = "http://loki:3100/loki/api/v1/push"

        with patch("src.app.core.tasks.sentry_task.settings", mock_settings):
            with patch("src.app.core.tasks.sentry_task.httpx.AsyncClient", return_value=mock_client):
                with patch("src.app.core.tasks.sentry_task.log") as mock_log:
                    from src.app.core.tasks.sentry_task import send_event_to_loki

                    await send_event_to_loki(
                        event_id="ok-event", message="All good", level="info"
                    )

                mock_log.info.assert_called_once()
                mock_log.error.assert_not_called()