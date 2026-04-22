"""
Расширенные тесты для LogContextService.
Покрывает непокрытые ветки: setup_request_ids, setup_request_context,
get_safe_context с реальным request, edge cases.
"""

import uuid
from unittest.mock import MagicMock, patch

import pytest

from src.app.core.services.log_context_service import LogContextService


def make_request(
    method: str = "GET",
    path: str = "/test",
    state_attrs: dict | None = None,
    headers: dict | None = None,
    client_host: str = "127.0.0.1",
) -> MagicMock:
    """Создаёт мок FastAPI Request."""
    request = MagicMock()
    request.method = method
    request.url.path = path
    request.url.__str__ = lambda self: f"http://testserver{path}"
    request.headers = headers or {}
    request.client = MagicMock()
    request.client.host = client_host

    state = MagicMock(spec=[])
    if state_attrs:
        for k, v in state_attrs.items():
            setattr(state, k, v)
    request.state = state
    return request


# ─── setup_request_ids ───────────────────────────────────────────────────────


class TestSetupRequestIds:
    """Тесты для setup_request_ids."""

    def test_generates_trace_id_if_missing(self):
        """Генерирует trace_id если его нет в state."""
        request = make_request()
        LogContextService.setup_request_ids(request)

        trace_id = request.state.trace_id
        assert len(trace_id) == 36  # UUID4 формат
        # валидный UUID
        uuid.UUID(trace_id)

    def test_preserves_existing_trace_id(self):
        """Не перезаписывает существующий trace_id."""
        existing_trace = "existing-trace-id-123"
        request = make_request(state_attrs={"trace_id": existing_trace})
        LogContextService.setup_request_ids(request)

        assert request.state.trace_id == existing_trace

    def test_uses_x_request_id_header(self):
        """Использует X-Request-ID из заголовков если есть."""
        request = make_request(headers={"X-Request-ID": "client-req-id-999"})
        LogContextService.setup_request_ids(request)

        assert request.state.request_id == "client-req-id-999"

    def test_generates_request_id_if_no_header(self):
        """Генерирует request_id если нет заголовка."""
        request = make_request()
        LogContextService.setup_request_ids(request)

        request_id = request.state.request_id
        assert len(request_id) == 36
        uuid.UUID(request_id)

    def test_multiple_calls_preserve_trace_id(self):
        """Повторный вызов не меняет trace_id."""
        request = make_request()
        LogContextService.setup_request_ids(request)
        trace_id_first = request.state.trace_id

        # второй вызов — trace_id уже есть в state
        request2 = make_request(state_attrs={"trace_id": trace_id_first})
        LogContextService.setup_request_ids(request2)

        assert request2.state.trace_id == trace_id_first


# ─── setup_request_context ───────────────────────────────────────────────────


class TestSetupRequestContext:
    """Тесты для setup_request_context."""

    def test_sets_client_ip(self):
        """Устанавливает client_ip в state."""
        request = make_request(client_host="192.168.1.100")

        with patch("src.app.core.services.log_context_service.get_client_ip", return_value="192.168.1.100"):
            with patch("src.app.core.services.log_context_service.get_scheme_and_host", return_value=("http", "localhost")):
                LogContextService.setup_request_context(request)

        assert request.state.client_ip == "192.168.1.100"

    def test_sets_scheme_and_host(self):
        """Устанавливает scheme и host в state."""
        request = make_request()

        with patch("src.app.core.services.log_context_service.get_client_ip", return_value="1.2.3.4"):
            with patch("src.app.core.services.log_context_service.get_scheme_and_host", return_value=("https", "example.com")):
                LogContextService.setup_request_context(request)

        assert request.state.scheme == "https"
        assert request.state.host == "example.com"

    def test_calls_setup_request_ids(self):
        """Вызывает setup_request_ids."""
        request = make_request()

        with patch.object(LogContextService, "setup_request_ids") as mock_ids:
            with patch("src.app.core.services.log_context_service.get_client_ip", return_value="1.2.3.4"):
                with patch("src.app.core.services.log_context_service.get_scheme_and_host", return_value=("http", "host")):
                    LogContextService.setup_request_context(request)

        mock_ids.assert_called_once_with(request)

    def test_uses_existing_client_ip_from_state(self):
        """Не перезаписывает client_ip если уже есть в state."""
        request = make_request(state_attrs={"client_ip": "10.0.0.1"})

        with patch("src.app.core.services.log_context_service.get_client_ip") as mock_get_ip:
            with patch("src.app.core.services.log_context_service.get_scheme_and_host", return_value=("http", "host")):
                LogContextService.setup_request_context(request)

        # get_client_ip не должен быть вызван если ip уже есть
        mock_get_ip.assert_not_called()
        assert request.state.client_ip == "10.0.0.1"

    def test_passes_trusted_proxies(self):
        """Передаёт trusted_proxies в get_client_ip и get_scheme_and_host."""
        request = make_request()
        proxies = ["10.0.0.1", "172.16.0.0/12"]

        with patch("src.app.core.services.log_context_service.get_client_ip", return_value="1.2.3.4") as mock_ip:
            with patch("src.app.core.services.log_context_service.get_scheme_and_host", return_value=("http", "host")) as mock_scheme:
                LogContextService.setup_request_context(request, trusted_proxies=proxies)

        mock_ip.assert_called_once_with(request, trusted_proxies=proxies)
        mock_scheme.assert_called_once_with(request, trusted_proxies=proxies)


# ─── extract_context_from_request edge cases ─────────────────────────────────


class TestExtractContextEdgeCases:
    """Edge cases для extract_context_from_request."""

    def test_extract_without_any_state_attrs(self):
        """Запрос без state атрибутов возвращает базовый контекст."""
        request = make_request()
        context = LogContextService.extract_context_from_request(request)

        assert isinstance(context, dict)
        assert "method" in context
        assert context["method"] == "GET"

    def test_extract_with_all_state_attrs(self):
        """Все state атрибуты корректно извлекаются."""
        request = make_request(
            state_attrs={
                "client_ip": "5.6.7.8",
                "trace_id": "trace-123",
                "request_id": "req-456",
                "status_code": 200,
                "process_time_ms": 42.5,
            }
        )
        context = LogContextService.extract_context_from_request(request)

        assert context["ip"] == "5.6.7.8"
        assert context["trace_id"] == "trace-123"
        assert context["request_id"] == "req-456"
        assert context["status"] == 200
        assert context["ms"] == 42.5

    def test_ua_default_when_no_header(self):
        """Без заголовка User-Agent — 'unknown'."""
        request = make_request(headers={})
        context = LogContextService.extract_context_from_request(request)

        assert context.get("ua") == "unknown"

    def test_url_from_effective_url_in_state(self):
        """URL берётся из state.effective_url если есть."""
        effective_url = "https://example.com/api/test"
        request = make_request(state_attrs={"effective_url": effective_url})
        context = LogContextService.extract_context_from_request(request)

        assert context.get("url") == effective_url


# ─── get_safe_context ─────────────────────────────────────────────────────────


class TestGetSafeContext:
    """Тесты для get_safe_context."""

    def test_always_returns_dict(self):
        """get_safe_context всегда возвращает dict."""
        request = make_request()
        result = LogContextService.get_safe_context(request)
        assert isinstance(result, dict)

    def test_returns_validated_context(self):
        """Возвращает контекст с заполненными критическими полями."""
        request = make_request()
        result = LogContextService.get_safe_context(request)

        # request_id и trace_id должны быть валидными UUID после validate_context
        assert result.get("request_id") is not None
        assert result.get("request_id") != "unknown"
        assert len(result["request_id"]) == 36

    def test_combines_extract_and_validate(self):
        """get_safe_context = extract + validate."""
        request = make_request(
            state_attrs={"client_ip": "9.9.9.9"},
            headers={"user-agent": "TestBrowser/2.0"},
        )
        result = LogContextService.get_safe_context(request)

        # из extract
        assert result.get("ip") == "9.9.9.9"
        assert result.get("ua") == "TestBrowser/2.0"
        # из validate — uuid для request_id
        assert len(result.get("request_id", "")) == 36