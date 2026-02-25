from fastapi import APIRouter
from fastapi.requests import Request
from fastapi.responses import ORJSONResponse

from src.app.core.logger import get_logger
from src.app.core.schemas.security import CSPReportResponse, CSPViolationReport

router = APIRouter(
    tags=["Security"],
    default_response_class=ORJSONResponse,
)

log = get_logger("security_router")


@router.post("/csp-report")
async def csp_report(
    request: Request, report_data: CSPViolationReport | None = None
) -> CSPReportResponse:
    """
    Эндпоинт для получения отчетов о нарушениях CSP с валидацией.

    Эндпоинт принимает JSON-полезную нагрузку с отчетом о нарушении CSP.
    Валидирует структуру отчета и логирует нарушения.

    Возвращает JSON-ответ со статусом "received" или "error". Если отчет
    успешно обработан, статус будет "received". При ошибке
    обработки статус будет "error" и ответ будет содержать сообщение об ошибке.

    :param request: Входящий запрос.
    :param report_data: Валидированные данные отчета о нарушении CSP.
    :return: JSON-ответ со статусом и опциональным сообщением об ошибке.
    """

    try:
        # Пробуем сначала валидировать через Pydantic
        if report_data:
            report = report_data.model_dump()
        else:
            # Fallback для legacy формата
            raw_report = await request.json()
            report = raw_report

        # Валидация обязательных полей
        if not report:
            raise ValueError("Получен пустой отчет")

        # Дополнительная валидация структуры
        if "csp-report" in report:
            violation = report["csp-report"]
        elif "body" in report:
            violation = report["body"]
        else:
            raise ValueError(
                "Неверная структура отчета - отсутствуют 'csp-report' или 'body'"
            )

        # Проверяем наличие document_uri
        if not violation.get("document_uri"):
            raise ValueError("Отсутствует document_uri в отчете о нарушении")

        log.warning(
            f"Обнаружено нарушение CSP: {violation.get('effective_directive')} "
            f"с {violation.get('document_uri')} - "
            f"заблокировано: {violation.get('blocked_uri', 'unknown')}"
        )

        return CSPReportResponse(status="received")

    except Exception as e:
        log.error(f"Ошибка обработки CSP отчета: {str(e)}")
        return CSPReportResponse(status="error", message=str(e))
