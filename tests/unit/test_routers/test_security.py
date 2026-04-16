"""
Тесты для security router.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import Request

from src.app.core.schemas.security import CSPReportResponse


@pytest.fixture
def mock_request():
    """Создает мок для Request."""
    request = MagicMock(spec=Request)
    return request


@pytest.fixture
def csp_report_data():
    """Валидные данные CSP отчета."""
    return {
        "csp-report": {
            "document-uri": "https://example.com",
            "referrer": "https://example.com",
            "violated-directive": "script-src",
            "effective-directive": "script-src",
            "original-policy": "default-src 'self'",
            "disposition": "report",
            "blocked-uri": "https://evil.com/script.js",
            "line-number": 10,
            "column-number": 5,
            "source-file": "https://example.com/index.html",
            "status-code": 200,
            "script-sample": "",
        }
    }


# --- csp_report ---


@pytest.mark.asyncio
@patch("src.app.routers.security.CSPReportService.process_report")
async def test_csp_report_success(mock_process_report, mock_request, csp_report_data):
    """Тест успешной обработки CSP отчета."""
    from src.app.routers.security import csp_report

    mock_request.json = AsyncMock(return_value=csp_report_data)
    mock_process_report.return_value = (
        "script-src",
        "https://example.com",
        "https://evil.com/script.js",
    )

    result = await csp_report(mock_request)

    assert isinstance(result, CSPReportResponse)
    assert result.status == "received"
    assert result.message is None
    mock_process_report.assert_called_once_with(csp_report_data)


@pytest.mark.asyncio
@patch("src.app.routers.security.CSPReportService.process_report")
async def test_csp_report_invalid_json(mock_process_report, mock_request):
    """Тест обработки невалидного JSON в CSP отчете."""
    from src.app.routers.security import csp_report

    mock_request.json = AsyncMock(side_effect=Exception("Invalid JSON"))

    result = await csp_report(mock_request)

    assert isinstance(result, CSPReportResponse)
    assert result.status == "error"
    assert "Invalid JSON" in result.message
    mock_process_report.assert_not_called()


@pytest.mark.asyncio
@patch("src.app.routers.security.CSPReportService.process_report")
async def test_csp_report_processing_error(mock_process_report, mock_request, csp_report_data):
    """Тест ошибки при обработке CSP отчета."""
    from src.app.routers.security import csp_report

    mock_request.json = AsyncMock(return_value=csp_report_data)
    mock_process_report.side_effect = Exception("Processing error")

    result = await csp_report(mock_request)

    assert isinstance(result, CSPReportResponse)
    assert result.status == "error"
    assert "Processing error" in result.message
