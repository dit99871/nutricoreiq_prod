"""
Тесты для exception_handlers.
"""

from unittest.mock import MagicMock, patch

import pytest
from fastapi import Request

from src.app.core.exception_handlers import (
    _is_bot_request,
    application_error_handler,
    not_found_exception_handler,
)
from src.app.core.exceptions import (
    AuthenticationError,
    CSRFTokenError,
    DatabaseError,
    ExternalServiceError,
)


def make_request(
    path: str = "/test",
    method: str = "GET",
    user_agent: str = "TestBrowser/1.0",
) -> MagicMock:
    request = MagicMock(spec=Request)
    request.url.path = path
    request.method = method
    request.headers = {"user-agent": user_agent}
    request.state = MagicMock(spec=[])
    return request


# --- _is_bot_request ---


@pytest.mark.parametrize(
    "path, expected_category",
    [
        ("/robots.txt", "legitimate_path"),
        ("/.well-known/acme-challenge/token", "legitimate_path"),
        ("/sitemap.xml", "legitimate_path"),
    ],
)
def test_is_bot_legitimate_paths(path, expected_category):
    is_bot, category = _is_bot_request(path, "SomeBot/1.0")
    assert is_bot is True
    assert category == expected_category


@pytest.mark.parametrize(
    "path",
    [
        "/wp-login.php",
        "/wp-admin/",
        "/phpmyadmin/",
        "/xmlrpc.php",
        "/administrator/",
    ],
)
def test_is_bot_suspicious_paths(path):
    is_bot, category = _is_bot_request(path, "Mozilla/5.0")
    assert is_bot is True
    assert category == "suspicious_path"


@pytest.mark.parametrize(
    "user_agent",
    [
        "curl/8.7.1",
        "python-requests/2.31",
        "Googlebot/2.1",
        "wget/1.21",
    ],
)
def test_is_bot_ua_based(user_agent):
    is_bot, category = _is_bot_request("/some/path", user_agent)
    assert is_bot is True
    assert category == "ua_based"


def test_is_bot_human():
    is_bot, category = _is_bot_request(
        "/user/profile",
        "Mozilla/5.0 (Windows NT 10.0) Chrome/120",
    )
    assert is_bot is False
    assert category == "human"


# --- not_found_exception_handler ---


def _make_404_exc():
    from starlette.exceptions import HTTPException

    return HTTPException(status_code=404)


def test_not_found_legitimate_bot_logs_info():
    request = make_request(path="/robots.txt")
    exc = _make_404_exc()

    with patch("src.app.core.exception_handlers.log") as mock_log:
        with patch("src.app.core.exception_handlers.LogContextService") as mock_lcs:
            mock_lcs.get_safe_context.return_value = {}
            mock_lcs.format_request_line.return_value = "GET /robots.txt"
            mock_lcs.format_context_string.return_value = ""
            not_found_exception_handler(request, exc)
        mock_log.info.assert_called_once()
        mock_log.warning.assert_not_called()


def test_not_found_suspicious_path_logs_warning():
    request = make_request(path="/wp-login.php")
    exc = _make_404_exc()

    with patch("src.app.core.exception_handlers.log") as mock_log:
        with patch("src.app.core.exception_handlers.LogContextService") as mock_lcs:
            mock_lcs.get_safe_context.return_value = {}
            mock_lcs.format_request_line.return_value = "POST /wp-login.php"
            mock_lcs.format_context_string.return_value = ""
            not_found_exception_handler(request, exc)
        mock_log.warning.assert_called_once()
        mock_log.info.assert_not_called()


def test_not_found_ua_based_bot_logs_warning():
    """curl и подобные — WARNING (попадут в fail2ban)."""
    request = make_request(path="/amazon/.env", user_agent="curl/8.7.1")
    exc = _make_404_exc()

    with patch("src.app.core.exception_handlers.log") as mock_log:
        with patch("src.app.core.exception_handlers.LogContextService") as mock_lcs:
            mock_lcs.get_safe_context.return_value = {}
            mock_lcs.format_request_line.return_value = "GET /amazon/.env"
            mock_lcs.format_context_string.return_value = ""
            not_found_exception_handler(request, exc)
        mock_log.warning.assert_called_once()


def test_not_found_human_logs_warning_with_referrer():
    request = make_request(path="/missing-page")
    request.headers = {
        "user-agent": "Mozilla/5.0 Chrome/120",
        "referer": "https://nutricoreiq.ru/",
    }
    exc = _make_404_exc()

    with patch("src.app.core.exception_handlers.log") as mock_log:
        with patch("src.app.core.exception_handlers.LogContextService") as mock_lcs:
            mock_lcs.get_safe_context.return_value = {}
            mock_lcs.format_request_line.return_value = "GET /missing-page"
            mock_lcs.format_context_string.return_value = ""
            not_found_exception_handler(request, exc)
        mock_log.warning.assert_called_once()


def test_not_found_grafana_path_no_logging():
    request = make_request(path="/apis/features.grafana.app/v0alpha1/test")
    exc = _make_404_exc()

    with patch("src.app.core.exception_handlers.log") as mock_log:
        not_found_exception_handler(request, exc)
    mock_log.info.assert_not_called()
    mock_log.warning.assert_not_called()


def test_not_found_returns_404():
    """Проверяем статус без мокания LogContextService (чтобы не ломать сериализацию)."""
    request = make_request(path="/missing")
    # устанавливаем state-атрибуты которые читает LogContextService
    request.state.request_id = "test-request-id"
    request.state.trace_id = "test-trace-id"
    request.state.client_ip = "1.2.3.4"
    request.state.process_time_ms = None
    request.state.status_code = None
    request.state.effective_url = None
    exc = _make_404_exc()
    response = not_found_exception_handler(request, exc)
    assert response.status_code == 404


# --- application_error_handler ---


@pytest.mark.asyncio
async def test_application_error_handler_database_error_logs_error():
    """DatabaseError — реальный сбой сервера, должен логироваться как ERROR."""
    request = make_request()
    exc = DatabaseError("DB connection failed")

    with patch("src.app.core.exception_handlers.log") as mock_log:
        with patch("src.app.core.exception_handlers.LogContextService") as mock_lcs:
            mock_lcs.get_safe_context.return_value = {}
            mock_lcs.format_request_line.return_value = "GET /test"
            mock_lcs.format_context_string.return_value = ""
            await application_error_handler(request, exc)
        mock_log.error.assert_called_once()
        mock_log.warning.assert_not_called()


@pytest.mark.asyncio
async def test_application_error_handler_external_service_error_logs_error():
    request = make_request()
    exc = ExternalServiceError("SMTP failed", service_name="SMTP")

    with patch("src.app.core.exception_handlers.log") as mock_log:
        with patch("src.app.core.exception_handlers.LogContextService") as mock_lcs:
            mock_lcs.get_safe_context.return_value = {}
            mock_lcs.format_request_line.return_value = "POST /test"
            mock_lcs.format_context_string.return_value = ""
            await application_error_handler(request, exc)
        mock_log.error.assert_called_once()
        mock_log.warning.assert_not_called()


@pytest.mark.asyncio
async def test_application_error_handler_csrf_error_logs_warning():
    """CSRFTokenError — штатный отказ, приложение сработало корректно → WARNING."""
    request = make_request()
    exc = CSRFTokenError()

    with patch("src.app.core.exception_handlers.log") as mock_log:
        with patch("src.app.core.exception_handlers.LogContextService") as mock_lcs:
            mock_lcs.get_safe_context.return_value = {}
            mock_lcs.format_request_line.return_value = "POST /test"
            mock_lcs.format_context_string.return_value = ""
            await application_error_handler(request, exc)
        mock_log.warning.assert_called_once()
        mock_log.error.assert_not_called()


@pytest.mark.asyncio
async def test_application_error_handler_auth_error_logs_warning():
    request = make_request()
    exc = AuthenticationError("Invalid credentials")

    with patch("src.app.core.exception_handlers.log") as mock_log:
        with patch("src.app.core.exception_handlers.LogContextService") as mock_lcs:
            mock_lcs.get_safe_context.return_value = {}
            mock_lcs.format_request_line.return_value = "POST /auth/login"
            mock_lcs.format_context_string.return_value = ""
            await application_error_handler(request, exc)
        mock_log.warning.assert_called_once()
        mock_log.error.assert_not_called()


@pytest.mark.asyncio
async def test_application_error_handler_returns_correct_status():
    request = make_request()
    exc = CSRFTokenError()

    with patch("src.app.core.exception_handlers.LogContextService"):
        response = await application_error_handler(request, exc)
    assert response.status_code == exc.status_code


@pytest.mark.asyncio
async def test_application_error_handler_response_has_message():
    request = make_request()
    exc = AuthenticationError("Неверные учетные данные")

    with patch("src.app.core.exception_handlers.LogContextService"):
        response = await application_error_handler(request, exc)

    import json

    body = json.loads(response.body)
    # ErrorDetail применяет to_upper=True к message
    assert body["error"]["message"] == "НЕВЕРНЫЕ УЧЕТНЫЕ ДАННЫЕ"
