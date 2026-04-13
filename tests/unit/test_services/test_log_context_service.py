"""
Тесты для LogContextService.
"""

from unittest.mock import MagicMock

from src.app.core.services.log_context_service import LogContextService


def make_request(
    method: str = "GET",
    path: str = "/test",
    state_attrs: dict | None = None,
    headers: dict | None = None,
) -> MagicMock:
    request = MagicMock()
    request.method = method
    request.url.path = path
    request.headers = headers or {}

    state = MagicMock(spec=[])
    if state_attrs:
        for k, v in state_attrs.items():
            setattr(state, k, v)

    request.state = state
    return request


# --- format_request_line ---

def test_format_request_line_get():
    request = make_request("GET", "/users")
    assert LogContextService.format_request_line(request) == "GET /users"


def test_format_request_line_post():
    request = make_request("POST", "/auth/login")
    assert LogContextService.format_request_line(request) == "POST /auth/login"


def test_format_request_line_root():
    request = make_request("HEAD", "/")
    assert LogContextService.format_request_line(request) == "HEAD /"


# --- format_context_string ---

def test_format_context_string_new_field_names():
    context = {
        "status": 200,
        "ip": "1.2.3.4",
        "ua": "Chrome/120",
        "ms": 5.2,
        "request_id": "abc-123",
        "trace_id": "xyz-456",
    }
    result = LogContextService.format_context_string(context)
    assert "status=200" in result
    assert "ip=1.2.3.4" in result
    assert "ua=Chrome/120" in result
    assert "ms=5.2" in result
    assert "request_id=abc-123" in result
    assert "trace_id=xyz-456" in result


def test_format_context_string_no_old_names():
    context = {"client_ip": "1.2.3.4", "user_agent": "Chrome", "ip": "5.6.7.8"}
    result = LogContextService.format_context_string(context)
    assert "client_ip" not in result
    assert "user_agent" not in result
    assert "ip=5.6.7.8" in result


def test_format_context_string_skips_none():
    context = {"status": None, "ip": "1.2.3.4", "ms": None}
    result = LogContextService.format_context_string(context)
    assert "status" not in result
    assert "ms" not in result
    assert "ip=1.2.3.4" in result


def test_format_context_string_skips_unknown():
    context = {"ip": "unknown", "request_id": "abc"}
    result = LogContextService.format_context_string(context)
    assert "ip" not in result
    assert "request_id=abc" in result


def test_format_context_string_empty():
    assert LogContextService.format_context_string({}) == ""


def test_format_context_string_order():
    context = {"trace_id": "t", "request_id": "r", "ip": "1.2.3.4", "status": 404}
    result = LogContextService.format_context_string(context)
    assert result.index("status=") < result.index("ip=") < result.index("request_id=") < result.index("trace_id=")


# --- extract_context_from_request ---

def test_extract_context_renames_client_ip_to_ip():
    request = make_request(state_attrs={"client_ip": "9.8.7.6"})
    context = LogContextService.extract_context_from_request(request)
    assert context.get("ip") == "9.8.7.6"
    assert "client_ip" not in context


def test_extract_context_ua_from_headers():
    request = make_request(headers={"user-agent": "TestAgent/1.0"})
    context = LogContextService.extract_context_from_request(request)
    assert context.get("ua") == "TestAgent/1.0"
    assert "user_agent" not in context


def test_extract_context_status_from_state():
    request = make_request(state_attrs={"status_code": 200})
    context = LogContextService.extract_context_from_request(request)
    assert context.get("status") == 200


def test_extract_context_ms_from_state():
    request = make_request(state_attrs={"process_time_ms": 12.5})
    context = LogContextService.extract_context_from_request(request)
    assert context.get("ms") == 12.5


# --- ensure_context_fields ---

def test_ensure_context_fields_adds_missing():
    result = LogContextService.ensure_context_fields({})
    assert result["ip"] == "unknown"
    assert result["ua"] == "unknown"
    assert result["request_id"] == "unknown"
    assert result["trace_id"] == "unknown"


def test_ensure_context_fields_no_old_names():
    result = LogContextService.ensure_context_fields({})
    assert "client_ip" not in result
    assert "user_agent" not in result
    assert "method" not in result


def test_ensure_context_fields_preserves_existing():
    context = {"ip": "1.2.3.4", "request_id": "abc"}
    result = LogContextService.ensure_context_fields(context)
    assert result["ip"] == "1.2.3.4"
    assert result["request_id"] == "abc"


# --- validate_context ---

def test_validate_context_generates_request_id_if_unknown():
    context = {"request_id": "unknown"}
    result = LogContextService.validate_context(context)
    assert result["request_id"] != "unknown"
    assert len(result["request_id"]) == 36


def test_validate_context_generates_trace_id_if_missing():
    result = LogContextService.validate_context({})
    assert len(result["trace_id"]) == 36