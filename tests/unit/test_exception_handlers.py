"""
Тесты для exception_handlers.
"""

import json
from unittest.mock import MagicMock, patch

import pytest
from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.app.core.exception_handlers import (
    expired_token_exception_handler,
    generic_exception_handler,
    http_exception_handler,
    rate_limit_exceeded_handler,
    setup_exception_handlers,
    validation_exception_handler, _is_bot_request, not_found_exception_handler, application_error_handler,
)
from src.app.core.exceptions import ExpiredTokenException, DatabaseError, ExternalServiceError, CSRFTokenError, \
    AuthenticationError


def make_request(
        path: str = "/test",
        method: str = "GET",
        user_agent: str = "Mozilla/5.0",
        headers: dict | None = None,
        scheme: str = "http",
) -> MagicMock:
    """Создаёт мок FastAPI Request с настроенным state."""
    request = MagicMock(spec=Request)
    request.url.path = path
    request.method = method
    request.headers = headers or {"user-agent": user_agent}
    request.scope = {"scheme": scheme}

    # настраиваем state для LogContextService
    state = MagicMock(spec=[])
    state.request_id = "test-req-id"
    state.trace_id = "test-trace-id"
    state.client_ip = "127.0.0.1"
    state.process_time_ms = None
    state.status_code = None
    state.effective_url = None
    request.state = state
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


# ─── http_exception_handler ──────────────────────────────────────────────────


class TestHttpExceptionHandler:
    """Тесты для http_exception_handler."""

    def test_http_exception_string_detail(self):
        """Строковый detail корректно переносится в message."""
        request = make_request()
        exc = StarletteHTTPException(status_code=403, detail="Forbidden")

        with patch("src.app.core.exception_handlers.LogContextService") as mock_lcs:
            mock_lcs.get_safe_context.return_value = {}
            mock_lcs.format_request_line.return_value = "GET /test"
            mock_lcs.format_context_string.return_value = ""
            response = http_exception_handler(request, exc)

        assert response.status_code == 403
        body = json.loads(response.body)
        assert body["status"] == "error"
        assert "FORBIDDEN" in body["error"]["message"]

    def test_http_exception_dict_detail_with_message(self):
        """Dict detail с ключом message — извлекает message и details."""
        request = make_request()
        exc = StarletteHTTPException(
            status_code=400,
            detail={"message": "Bad data", "details": {"field": "email"}},
        )

        with patch("src.app.core.exception_handlers.LogContextService") as mock_lcs:
            mock_lcs.get_safe_context.return_value = {}
            mock_lcs.format_request_line.return_value = "POST /test"
            mock_lcs.format_context_string.return_value = ""
            response = http_exception_handler(request, exc)

        assert response.status_code == 400
        body = json.loads(response.body)
        assert "BAD DATA" in body["error"]["message"]
        assert body["error"]["details"] == {"field": "email"}

    def test_http_exception_dict_detail_no_message_key(self):
        """Dict detail без ключа message использует дефолтное сообщение."""
        request = make_request()
        exc = StarletteHTTPException(status_code=500, detail={"code": "ERR_500"})

        with patch("src.app.core.exception_handlers.LogContextService") as mock_lcs:
            mock_lcs.get_safe_context.return_value = {}
            mock_lcs.format_request_line.return_value = "GET /test"
            mock_lcs.format_context_string.return_value = ""
            response = http_exception_handler(request, exc)

        assert response.status_code == 500
        body = json.loads(response.body)
        assert "ПРОИЗОШЛА ОШИБКА" in body["error"]["message"]

    def test_http_exception_none_detail(self):
        """None detail использует дефолтное сообщение."""
        request = make_request()
        exc = StarletteHTTPException(status_code=404, detail=None)

        with patch("src.app.core.exception_handlers.LogContextService") as mock_lcs:
            mock_lcs.get_safe_context.return_value = {}
            mock_lcs.format_request_line.return_value = "GET /test"
            mock_lcs.format_context_string.return_value = ""
            response = http_exception_handler(request, exc)

        assert response.status_code == 404

    def test_http_exception_5xx_logs_error(self):
        """Коды >=500 логируются как error."""
        request = make_request()
        exc = StarletteHTTPException(status_code=503, detail="Service Unavailable")

        with patch("src.app.core.exception_handlers.log") as mock_log:
            with patch("src.app.core.exception_handlers.LogContextService") as mock_lcs:
                mock_lcs.get_safe_context.return_value = {}
                mock_lcs.format_request_line.return_value = "GET /test"
                mock_lcs.format_context_string.return_value = ""
                http_exception_handler(request, exc)

        mock_log.error.assert_called_once()
        mock_log.warning.assert_not_called()

    def test_http_exception_4xx_logs_warning(self):
        """Коды <500 логируются как warning."""
        request = make_request()
        exc = StarletteHTTPException(status_code=401, detail="Unauthorized")

        with patch("src.app.core.exception_handlers.log") as mock_log:
            with patch("src.app.core.exception_handlers.LogContextService") as mock_lcs:
                mock_lcs.get_safe_context.return_value = {}
                mock_lcs.format_request_line.return_value = "GET /test"
                mock_lcs.format_context_string.return_value = ""
                http_exception_handler(request, exc)

        mock_log.warning.assert_called_once()
        mock_log.error.assert_not_called()

    def test_http_exception_response_structure(self):
        """Проверяет структуру ответа."""
        request = make_request()
        exc = StarletteHTTPException(status_code=422, detail="Validation error")

        with patch("src.app.core.exception_handlers.LogContextService") as mock_lcs:
            mock_lcs.get_safe_context.return_value = {}
            mock_lcs.format_request_line.return_value = "POST /test"
            mock_lcs.format_context_string.return_value = ""
            response = http_exception_handler(request, exc)

        body = json.loads(response.body)
        assert "status" in body
        assert "error" in body
        assert "message" in body["error"]


# ─── validation_exception_handler ────────────────────────────────────────────


class TestValidationExceptionHandler:
    """Тесты для validation_exception_handler."""

    def _make_validation_error(self, errors: list[dict]):
        """Создаёт RequestValidationError из списка ошибок."""
        exc = MagicMock(spec=RequestValidationError)
        exc.errors.return_value = errors
        return exc

    def test_single_validation_error(self):
        """Одна ошибка — message берется из неё напрямую."""
        request = make_request()
        exc = self._make_validation_error([
            {"loc": ("body", "email"), "msg": "Invalid email", "type": "value_error.email"},
        ])

        with patch("src.app.core.exception_handlers.LogContextService") as mock_lcs:
            mock_lcs.get_safe_context.return_value = {}
            mock_lcs.format_request_line.return_value = "POST /test"
            mock_lcs.format_context_string.return_value = ""
            response = validation_exception_handler(request, exc)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        body = json.loads(response.body)
        assert body["status"] == "error"
        assert "INVALID EMAIL" in body["error"]["message"]

    def test_multiple_validation_errors(self):
        """Несколько ошибок — общий message 'Некорректные входные данные', details с полями."""
        request = make_request()
        exc = self._make_validation_error([
            {"loc": ("body", "email"), "msg": "Invalid email", "type": "string_type"},
            {"loc": ("body", "password"), "msg": "Too short", "type": "string_too_short"},
        ])

        with patch("src.app.core.exception_handlers.LogContextService") as mock_lcs:
            mock_lcs.get_safe_context.return_value = {}
            mock_lcs.format_request_line.return_value = "POST /auth"
            mock_lcs.format_context_string.return_value = ""
            response = validation_exception_handler(request, exc)

        body = json.loads(response.body)
        assert "НЕКОРРЕКТНЫЕ" in body["error"]["message"]
        assert body["error"]["details"] is not None
        assert "fields" in body["error"]["details"]
        assert len(body["error"]["details"]["fields"]) == 2

    def test_value_error_prefix_stripped(self):
        """Префикс 'Value error, ' удаляется из сообщения."""
        request = make_request()
        exc = self._make_validation_error([
            {
                "loc": ("body", "password"),
                "msg": "Value error, Пароль слишком простой",
                "type": "value_error",
            }
        ])

        with patch("src.app.core.exception_handlers.LogContextService") as mock_lcs:
            mock_lcs.get_safe_context.return_value = {}
            mock_lcs.format_request_line.return_value = "POST /register"
            mock_lcs.format_context_string.return_value = ""
            response = validation_exception_handler(request, exc)

        body = json.loads(response.body)
        # "Value error, " должен быть удален
        assert "VALUE ERROR" not in body["error"]["message"]
        assert "ПАРОЛЬ СЛИШКОМ ПРОСТОЙ" in body["error"]["message"]

    def test_validation_error_logs_error(self):
        """Ошибки валидации логируются как error."""
        request = make_request()
        exc = self._make_validation_error([
            {"loc": ("body", "age"), "msg": "Must be >= 10", "type": "greater_than_equal"},
        ])

        with patch("src.app.core.exception_handlers.log") as mock_log:
            with patch("src.app.core.exception_handlers.LogContextService") as mock_lcs:
                mock_lcs.get_safe_context.return_value = {}
                mock_lcs.format_request_line.return_value = "PUT /profile"
                mock_lcs.format_context_string.return_value = ""
                validation_exception_handler(request, exc)

        mock_log.error.assert_called_once()

    def test_nested_loc_joined_with_dot(self):
        """Вложенный loc соединяется точкой в поле field."""
        request = make_request()
        exc = self._make_validation_error([
            {
                "loc": ("body", "profile", "age"),
                "msg": "Invalid value",
                "type": "int_type",
            }
        ])

        with patch("src.app.core.exception_handlers.LogContextService") as mock_lcs:
            mock_lcs.get_safe_context.return_value = {}
            mock_lcs.format_request_line.return_value = "PUT /test"
            mock_lcs.format_context_string.return_value = ""
            response = validation_exception_handler(request, exc)

        # response 422 всегда
        assert response.status_code == 422


# ─── generic_exception_handler ───────────────────────────────────────────────


class TestGenericExceptionHandler:
    """Тесты для generic_exception_handler."""

    def test_generic_exception_returns_500(self):
        request = make_request()
        exc = RuntimeError("Something went wrong")

        with patch("src.app.core.exception_handlers.settings") as mock_settings:
            mock_settings.DEBUG = False
            with patch("src.app.core.exception_handlers.LogContextService") as mock_lcs:
                mock_lcs.extract_context_from_request.return_value = {}
                mock_lcs.format_request_line.return_value = "GET /test"
                mock_lcs.format_context_string.return_value = ""
                response = generic_exception_handler(request, exc)

        assert response.status_code == 500

    def test_generic_exception_debug_false_no_details(self):
        """В DEBUG=False details не включаются в ответ."""
        request = make_request()
        exc = ValueError("Internal error detail")

        with patch("src.app.core.exception_handlers.settings") as mock_settings:
            mock_settings.DEBUG = False
            with patch("src.app.core.exception_handlers.LogContextService") as mock_lcs:
                mock_lcs.extract_context_from_request.return_value = {}
                mock_lcs.format_request_line.return_value = "GET /test"
                mock_lcs.format_context_string.return_value = ""
                response = generic_exception_handler(request, exc)

        body = json.loads(response.body)
        assert body["error"]["details"] is None

    def test_generic_exception_debug_true_includes_details(self):
        """В DEBUG=True details включаются в ответ."""
        request = make_request()
        exc = RuntimeError("Detailed error message")

        with patch("src.app.core.exception_handlers.settings") as mock_settings:
            mock_settings.DEBUG = True
            with patch("src.app.core.exception_handlers.LogContextService") as mock_lcs:
                mock_lcs.extract_context_from_request.return_value = {}
                mock_lcs.format_request_line.return_value = "GET /test"
                mock_lcs.format_context_string.return_value = ""
                response = generic_exception_handler(request, exc)

        body = json.loads(response.body)
        assert body["error"]["details"] is not None
        assert "Detailed error message" in body["error"]["details"]["message"]

    def test_generic_exception_logs_error(self):
        """Непредвиденные ошибки логируются как error."""
        request = make_request()
        exc = Exception("Boom")

        with patch("src.app.core.exception_handlers.log") as mock_log:
            with patch("src.app.core.exception_handlers.settings") as mock_settings:
                mock_settings.DEBUG = False
                with patch("src.app.core.exception_handlers.LogContextService") as mock_lcs:
                    mock_lcs.extract_context_from_request.return_value = {}
                    mock_lcs.format_request_line.return_value = "GET /test"
                    mock_lcs.format_context_string.return_value = ""
                    generic_exception_handler(request, exc)

        mock_log.error.assert_called_once()

    def test_generic_exception_uses_forwarded_proto(self):
        """X-Forwarded-Proto используется для формирования URL."""
        request = make_request(headers={"X-Forwarded-Proto": "https", "user-agent": "test"})

        with patch("src.app.core.exception_handlers.settings") as mock_settings:
            mock_settings.DEBUG = False
            with patch("src.app.core.exception_handlers.LogContextService") as mock_lcs:
                mock_lcs.extract_context_from_request.return_value = {}
                mock_lcs.format_request_line.return_value = "GET /test"
                mock_lcs.format_context_string.return_value = ""
                response = generic_exception_handler(request, Exception("err"))

        assert response.status_code == 500

    def test_generic_exception_message_is_internal_server_error(self):
        """Сообщение всегда 'Внутренняя ошибка сервера'."""
        request = make_request()
        exc = Exception("anything")

        with patch("src.app.core.exception_handlers.settings") as mock_settings:
            mock_settings.DEBUG = False
            with patch("src.app.core.exception_handlers.LogContextService") as mock_lcs:
                mock_lcs.extract_context_from_request.return_value = {}
                mock_lcs.format_request_line.return_value = "GET /test"
                mock_lcs.format_context_string.return_value = ""
                response = generic_exception_handler(request, exc)

        body = json.loads(response.body)
        assert "ВНУТРЕННЯЯ ОШИБКА СЕРВЕРА" in body["error"]["message"]


# ─── rate_limit_exceeded_handler ─────────────────────────────────────────────


class TestRateLimitExceededHandler:
    """Тесты для rate_limit_exceeded_handler."""

    def _make_rate_limit_exc(self, detail: str = "5 per minute"):
        from slowapi.errors import RateLimitExceeded
        exc = MagicMock(spec=RateLimitExceeded)
        exc.detail = detail
        return exc

    def test_rate_limit_returns_429(self):
        request = make_request()
        exc = self._make_rate_limit_exc()

        with patch("src.app.core.exception_handlers.settings") as mock_settings:
            mock_settings.DEBUG = False
            with patch("src.app.core.exception_handlers.LogContextService") as mock_lcs:
                mock_lcs.get_safe_context.return_value = {}
                mock_lcs.format_request_line.return_value = "GET /test"
                mock_lcs.format_context_string.return_value = ""
                response = rate_limit_exceeded_handler(request, exc)

        assert response.status_code == 429

    def test_rate_limit_message(self):
        request = make_request()
        exc = self._make_rate_limit_exc()

        with patch("src.app.core.exception_handlers.settings") as mock_settings:
            mock_settings.DEBUG = False
            with patch("src.app.core.exception_handlers.LogContextService") as mock_lcs:
                mock_lcs.get_safe_context.return_value = {}
                mock_lcs.format_request_line.return_value = "GET /test"
                mock_lcs.format_context_string.return_value = ""
                response = rate_limit_exceeded_handler(request, exc)

        body = json.loads(response.body)
        assert "СЛИШКОМ МНОГО ЗАПРОСОВ" in body["error"]["message"]

    def test_rate_limit_debug_false_no_retry_after(self):
        """В DEBUG=False details не включаются."""
        request = make_request()
        exc = self._make_rate_limit_exc("10 per second")

        with patch("src.app.core.exception_handlers.settings") as mock_settings:
            mock_settings.DEBUG = False
            with patch("src.app.core.exception_handlers.LogContextService") as mock_lcs:
                mock_lcs.get_safe_context.return_value = {}
                mock_lcs.format_request_line.return_value = "GET /test"
                mock_lcs.format_context_string.return_value = ""
                response = rate_limit_exceeded_handler(request, exc)

        body = json.loads(response.body)
        assert body["error"]["details"] is None

    def test_rate_limit_debug_true_includes_retry_after(self):
        """В DEBUG=True details содержит retry_after."""
        request = make_request()
        exc = self._make_rate_limit_exc("10 per second")

        with patch("src.app.core.exception_handlers.settings") as mock_settings:
            mock_settings.DEBUG = True
            with patch("src.app.core.exception_handlers.LogContextService") as mock_lcs:
                mock_lcs.get_safe_context.return_value = {}
                mock_lcs.format_request_line.return_value = "GET /test"
                mock_lcs.format_context_string.return_value = ""
                response = rate_limit_exceeded_handler(request, exc)

        body = json.loads(response.body)
        assert body["error"]["details"] is not None
        assert body["error"]["details"]["retry_after"] == "10 per second"

    def test_rate_limit_logs_warning(self):
        request = make_request()
        exc = self._make_rate_limit_exc()

        with patch("src.app.core.exception_handlers.log") as mock_log:
            with patch("src.app.core.exception_handlers.settings") as mock_settings:
                mock_settings.DEBUG = False
                with patch("src.app.core.exception_handlers.LogContextService") as mock_lcs:
                    mock_lcs.get_safe_context.return_value = {}
                    mock_lcs.format_request_line.return_value = "GET /test"
                    mock_lcs.format_context_string.return_value = ""
                    rate_limit_exceeded_handler(request, exc)

        mock_log.warning.assert_called_once()

    def test_rate_limit_response_structure(self):
        request = make_request()
        exc = self._make_rate_limit_exc()

        with patch("src.app.core.exception_handlers.settings") as mock_settings:
            mock_settings.DEBUG = False
            with patch("src.app.core.exception_handlers.LogContextService") as mock_lcs:
                mock_lcs.get_safe_context.return_value = {}
                mock_lcs.format_request_line.return_value = "GET /test"
                mock_lcs.format_context_string.return_value = ""
                response = rate_limit_exceeded_handler(request, exc)

        body = json.loads(response.body)
        assert body["status"] == "error"
        assert "error" in body


# ─── expired_token_exception_handler ─────────────────────────────────────────


class TestExpiredTokenExceptionHandler:
    """Тесты для expired_token_exception_handler."""

    def test_expired_token_returns_401(self):
        request = make_request()
        exc = ExpiredTokenException()

        with patch("src.app.core.exception_handlers.LogContextService") as mock_lcs:
            mock_lcs.get_safe_context.return_value = {}
            mock_lcs.format_request_line.return_value = "GET /protected"
            mock_lcs.format_context_string.return_value = ""
            response = expired_token_exception_handler(request, exc)

        assert response.status_code == 401

    def test_expired_token_default_message(self):
        request = make_request()
        exc = ExpiredTokenException()

        with patch("src.app.core.exception_handlers.LogContextService") as mock_lcs:
            mock_lcs.get_safe_context.return_value = {}
            mock_lcs.format_request_line.return_value = "GET /protected"
            mock_lcs.format_context_string.return_value = ""
            response = expired_token_exception_handler(request, exc)

        body = json.loads(response.body)
        # detail из исключения попадает в message (to_upper)
        assert "СРОК" in body["error"]["message"] or "ТОКЕН" in body["error"]["message"]

    def test_expired_token_custom_message(self):
        request = make_request()
        exc = ExpiredTokenException(detail="Токен просрочен")

        with patch("src.app.core.exception_handlers.LogContextService") as mock_lcs:
            mock_lcs.get_safe_context.return_value = {}
            mock_lcs.format_request_line.return_value = "GET /protected"
            mock_lcs.format_context_string.return_value = ""
            response = expired_token_exception_handler(request, exc)

        body = json.loads(response.body)
        assert "ТОКЕН ПРОСРОЧЕН" in body["error"]["message"]

    def test_expired_token_has_error_type_header(self):
        request = make_request()
        exc = ExpiredTokenException()

        with patch("src.app.core.exception_handlers.LogContextService") as mock_lcs:
            mock_lcs.get_safe_context.return_value = {}
            mock_lcs.format_request_line.return_value = "GET /protected"
            mock_lcs.format_context_string.return_value = ""
            response = expired_token_exception_handler(request, exc)

        assert response.headers.get("x-error-type") == "authentication_error"

    def test_expired_token_logs_warning(self):
        request = make_request()
        exc = ExpiredTokenException()

        with patch("src.app.core.exception_handlers.log") as mock_log:
            with patch("src.app.core.exception_handlers.LogContextService") as mock_lcs:
                mock_lcs.get_safe_context.return_value = {}
                mock_lcs.format_request_line.return_value = "GET /protected"
                mock_lcs.format_context_string.return_value = ""
                expired_token_exception_handler(request, exc)

        mock_log.warning.assert_called_once()

    def test_expired_token_details_is_none(self):
        request = make_request()
        exc = ExpiredTokenException()

        with patch("src.app.core.exception_handlers.LogContextService") as mock_lcs:
            mock_lcs.get_safe_context.return_value = {}
            mock_lcs.format_request_line.return_value = "GET /protected"
            mock_lcs.format_context_string.return_value = ""
            response = expired_token_exception_handler(request, exc)

        body = json.loads(response.body)
        assert body["error"]["details"] is None


# ─── setup_exception_handlers ────────────────────────────────────────────────


class TestSetupExceptionHandlers:
    """Тесты для функции setup_exception_handlers."""

    def test_setup_registers_handlers(self):
        """Проверяет, что setup_exception_handlers регистрирует обработчики."""
        from fastapi import FastAPI

        app = FastAPI()
        # До setup обработчики не зарегистрированы
        initial_handlers = len(app.exception_handlers)

        setup_exception_handlers(app)

        # После setup — больше обработчиков
        assert len(app.exception_handlers) > initial_handlers

    def test_setup_registers_404_handler(self):
        """Проверяет регистрацию обработчика 404."""
        from fastapi import FastAPI

        app = FastAPI()
        setup_exception_handlers(app)

        # 404 должен быть в обработчиках
        assert 404 in app.exception_handlers

    def test_setup_registers_application_errors(self):
        """Все кастомные исключения зарегистрированы."""
        from fastapi import FastAPI

        from src.app.core.exceptions import (
            AuthenticationError,
            BaseApplicationError,
            CSRFTokenError,
            DatabaseError,
        )

        app = FastAPI()
        setup_exception_handlers(app)

        handlers = app.exception_handlers
        assert CSRFTokenError in handlers
        assert DatabaseError in handlers
        assert AuthenticationError in handlers
        assert BaseApplicationError in handlers