"""
Модуль для обработки CSP отчетов.
"""

from typing import Any, Dict

from src.app.core.logger import get_logger

log = get_logger("csp_service")


class CSPReportService:
    """Сервис для обработки CSP отчетов."""

    @staticmethod
    def extract_violation_data(report: Dict[str, Any]) -> Dict[str, Any]:
        """
        Извлекает данные о нарушении из CSP отчета.

        :param report: Сырой CSP отчет от браузера
        :return: Dict с данными о нарушении
        :raises ValueError: Если отчет пустой или не содержит данных о нарушении
        """

        if not report:
            raise ValueError("Получен пустой отчет")

        violation = None

        # извлекаем данные о нарушении из разных форматов
        if "csp-report" in report:
            violation_data = report["csp-report"]
            if isinstance(violation_data, dict):
                violation = violation_data
            else:
                violation = {
                    "document-uri": str(violation_data) if violation_data else "unknown"
                }

        elif "body" in report:
            violation_data = report["body"]
            if isinstance(violation_data, dict):
                violation = violation_data
            elif violation_data is not None:
                violation = {"document-uri": str(violation_data)}
            else:
                violation = {"document-uri": "unknown"}

        # если все еще нет violation, создаем базовую структуру
        if not violation:
            violation = {"document-uri": "unknown"}

        return violation

    @staticmethod
    def validate_violation(violation: Dict[str, Any]) -> str:
        """
        Валидирует и извлекает document_uri из нарушения.

        :param violation: Данные о нарушении
        :return: document_uri
        :raises ValueError: Если document_uri отсутствует
        """

        # поддерживаем разные форматы имен полей
        doc_uri = violation.get("document-uri") or violation.get("document_uri")

        if not doc_uri:
            log.error("VIOLATION WITHOUT document_uri: %s", violation)
            raise ValueError("Отсутствует document_uri в отчете о нарушении")

        return doc_uri

    @staticmethod
    def extract_violation_details(violation: Dict[str, Any]) -> tuple[str, str, str]:
        """
        Извлекает детали нарушения для логирования.

        :param violation: Данные о нарушении
        :return: Кортеж (effective_directive, document_uri, blocked_uri)
        """

        doc_uri = CSPReportService.validate_violation(violation)

        # поддерживаем разные форматы имен полей
        effective_directive = (
            violation.get("effective-directive")
            or violation.get("effective_directive")
            or violation.get("violated-directive")
            or "unknown"
        )

        blocked_uri = (
            violation.get("blocked-uri") or violation.get("blocked_uri") or "unknown"
        )

        return effective_directive, doc_uri, blocked_uri

    @staticmethod
    def process_report(report: Dict[str, Any]) -> tuple[str, str, str]:
        """
        Обрабатывает CSP отчет и возвращает детали нарушения.

        :param report: Сырой CSP отчет от браузера
        :return: Кортеж (effective_directive, document_uri, blocked_uri)
        :raises ValueError: Если отчет невалидный
        """

        violation = CSPReportService.extract_violation_data(report)

        return CSPReportService.extract_violation_details(violation)
