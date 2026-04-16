"""
Тесты для CSPReportService.
"""

import pytest

from src.app.core.services.csp_service import CSPReportService


class TestCSPReportService:
    """Тесты для CSPReportService."""

    def test_extract_violation_data_with_csp_report_dict(self):
        """Проверяем извлечение данных из csp-report формата (dict)."""
        report = {
            "csp-report": {
                "document-uri": "https://example.com",
                "violated-directive": "script-src",
                "blocked-uri": "https://evil.com"
            }
        }
        
        result = CSPReportService.extract_violation_data(report)
        
        assert result["document-uri"] == "https://example.com"
        assert result["violated-directive"] == "script-src"
        assert result["blocked-uri"] == "https://evil.com"

    def test_extract_violation_data_with_csp_report_string(self):
        """Проверяем извлечение данных из csp-report формата (string)."""
        report = {
            "csp-report": "Some violation data"
        }
        
        result = CSPReportService.extract_violation_data(report)
        
        assert result["document-uri"] == "Some violation data"
        assert "violated-directive" not in result
        assert "blocked-uri" not in result

    def test_extract_violation_data_with_body_dict(self):
        """Проверяем извлечение данных из body формата (dict)."""
        report = {
            "body": {
                "document-uri": "https://example.org",
                "violated-directive": "style-src",
                "blocked-uri": "https://malicious.org"
            }
        }
        
        result = CSPReportService.extract_violation_data(report)
        
        assert result["document-uri"] == "https://example.org"
        assert result["violated-directive"] == "style-src"
        assert result["blocked-uri"] == "https://malicious.org"

    def test_extract_violation_data_with_body_string(self):
        """Проверяем извлечение данных из body формата (string)."""
        report = {
            "body": "Body violation data"
        }
        
        result = CSPReportService.extract_violation_data(report)
        
        assert result["document-uri"] == "Body violation data"
        assert "violated-directive" not in result
        assert "blocked-uri" not in result

    def test_extract_violation_data_with_body_none(self):
        """Проверяем извлечение данных из body формата (None)."""
        report = {
            "body": None
        }
        
        result = CSPReportService.extract_violation_data(report)
        
        assert result["document-uri"] == "unknown"
        assert "violated-directive" not in result
        assert "blocked-uri" not in result

    def test_extract_violation_data_with_empty_report(self):
        """Проверяем обработку пустого отчета."""
        report = {}
        
        with pytest.raises(ValueError, match="Получен пустой отчет"):
            CSPReportService.extract_violation_data(report)

    def test_extract_violation_data_with_none_report(self):
        """Проверяем обработку None отчета."""
        report = None
        
        with pytest.raises(ValueError, match="Получен пустой отчет"):
            CSPReportService.extract_violation_data(report)

    def test_extract_violation_data_with_no_violation_keys(self):
        """Проверяем создание базовой структуры при отсутствии ключей."""
        report = {
            "some-other-key": "some-value"
        }
        
        result = CSPReportService.extract_violation_data(report)
        
        assert result["document-uri"] == "unknown"
        # Проверяем только базовые поля, которые должны быть в violation
        assert "document-uri" in result

    def test_extract_violation_data_complex_csp_report(self):
        """Проверяем извлечение данных из сложного csp-report."""
        report = {
            "csp-report": {
                "document-uri": "https://example.com/page",
                "referrer": "https://google.com",
                "violated-directive": "script-src",
                "effective-directive": "script-src",
                "original-policy": "script-src 'self'",
                "disposition": "report",
                "blocked-uri": "https://evil.com/script.js",
                "line-number": 15,
                "column-number": 25,
                "source-file": "https://example.com/app.js"
            }
        }
        
        result = CSPReportService.extract_violation_data(report)
        
        assert result["document-uri"] == "https://example.com/page"
        assert result["violated-directive"] == "script-src"
        assert result["blocked-uri"] == "https://evil.com/script.js"
        assert result["referrer"] == "https://google.com"
        assert result["effective-directive"] == "script-src"

    def test_process_report_basic(self):
        """Проверяем базовую обработку отчета."""
        report = {
            "csp-report": {
                "document-uri": "https://example.com",
                "violated-directive": "script-src",
                "blocked-uri": "https://evil.com"
            }
        }
        
        effective_directive, doc_uri, blocked_uri = CSPReportService.process_report(report)
        
        assert effective_directive == "script-src"
        assert doc_uri == "https://example.com"
        assert blocked_uri == "https://evil.com"

    def test_validate_violation_success(self):
        """Проверяем успешную валидацию нарушения."""
        violation = {
            "document-uri": "https://example.com",
            "violated-directive": "script-src"
        }
        
        result = CSPReportService.validate_violation(violation)
        
        assert result == "https://example.com"

    def test_validate_violation_missing_document_uri(self):
        """Проверяем валидацию нарушения без document-uri."""
        violation = {
            "violated-directive": "script-src"
        }
        
        with pytest.raises(ValueError, match="Отсутствует document_uri"):
            CSPReportService.validate_violation(violation)

    def test_extract_violation_details_success(self):
        """Проверяем извлечение деталей нарушения."""
        violation = {
            "document-uri": "https://example.com",
            "violated-directive": "script-src",
            "blocked-uri": "https://evil.com"
        }
        
        effective_directive, doc_uri, blocked_uri = CSPReportService.extract_violation_details(violation)
        
        assert effective_directive == "script-src"
        assert doc_uri == "https://example.com"
        assert blocked_uri == "https://evil.com"

    def test_extract_violation_details_missing_fields(self):
        """Проверяем извлечение деталей при отсутствующих полях."""
        violation = {
            "document-uri": "https://example.com"
        }
        
        effective_directive, doc_uri, blocked_uri = CSPReportService.extract_violation_details(violation)
        
        assert effective_directive == "unknown"
        assert doc_uri == "https://example.com"
        assert blocked_uri == "unknown"

    def test_process_report_without_document_uri_raises_exception(self):
        """Проверяем, что отчет без document-uri вызывает исключение."""
        report = {
            "csp-report": {
                "violated-directive": "script-src",
                "blocked-uri": "https://evil.com"
            }
        }
        
        with pytest.raises(ValueError, match="Отсутствует document_uri"):
            CSPReportService.process_report(report)

    def test_process_report_without_blocked_uri(self):
        """Проверяем обработку отчета без blocked-uri."""
        report = {
            "csp-report": {
                "document-uri": "https://example.com",
                "violated-directive": "script-src"
            }
        }
        
        effective_directive, doc_uri, blocked_uri = CSPReportService.process_report(report)
        
        assert effective_directive == "script-src"
        assert doc_uri == "https://example.com"
        assert blocked_uri == "unknown"

    def test_process_report_with_body_format(self):
        """Проверяем обработку отчета в body формате."""
        report = {
            "body": {
                "document-uri": "https://example.org",
                "violated-directive": "style-src",
                "blocked-uri": "https://malicious.org/style.css"
            }
        }
        
        effective_directive, doc_uri, blocked_uri = CSPReportService.process_report(report)
        
        assert effective_directive == "style-src"
        assert doc_uri == "https://example.org"
        assert blocked_uri == "https://malicious.org/style.css"

    def test_process_report_exception_handling(self):
        """Проверяем обработку исключений при обработке отчета."""
        report = {
            "csp-report": {
                "document-uri": "https://example.com",
                "violated-directive": "script-src",
                "blocked-uri": "https://evil.com"
            }
        }
        
        # Метод process_report должен вызывать extract_violation_data
        # и возвращать кортеж из трех элементов
        result = CSPReportService.process_report(report)
        
        assert isinstance(result, tuple)
        assert len(result) == 3
        assert all(isinstance(item, str) for item in result)

    def test_extract_violation_data_is_static_method(self):
        """Проверяем, что extract_violation_data является статическим методом."""
        import inspect
        assert inspect.isfunction(CSPReportService.extract_violation_data)
        assert inspect.ismethod(CSPReportService.extract_violation_data) is False

    def test_process_report_is_static_method(self):
        """Проверяем, что process_report является статическим методом."""
        import inspect
        assert inspect.isfunction(CSPReportService.process_report)
        assert inspect.ismethod(CSPReportService.process_report) is False

    def test_extract_violation_data_preserves_original_data(self):
        """Проверяем, что оригинальные данные не изменяются."""
        original_report = {
            "csp-report": {
                "document-uri": "https://example.com",
                "violated-directive": "script-src",
                "blocked-uri": "https://evil.com"
            }
        }
        report_copy = original_report.copy()
        report_copy["csp-report"] = report_copy["csp-report"].copy()
        
        result = CSPReportService.extract_violation_data(original_report)
        
        # Оригинальные данные должны остаться без изменений
        assert original_report == report_copy
        assert result is not original_report
