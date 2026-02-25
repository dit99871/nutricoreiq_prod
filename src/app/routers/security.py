from fastapi import APIRouter
from fastapi.requests import Request
from fastapi.responses import ORJSONResponse

from src.app.core.logger import get_logger
from src.app.core.schemas.security import CSPReportResponse

router = APIRouter(
    tags=["Security"],
    default_response_class=ORJSONResponse,
)

log = get_logger("security_router")


@router.post("/csp-report")
async def csp_report(request: Request) -> CSPReportResponse:
    """
    Эндпоинт для получения отчетов о нарушениях CSP с валидацией.

    Эндпоинт принимает JSON-полезную нагрузку с отчетом о нарушении CSP.
    Валидирует структуру отчета и логирует нарушения.

    Возвращает JSON-ответ со статусом "received" или "error". Если отчет
    успешно обработан, статус будет "received". При ошибке
    обработки статус будет "error" и ответ будет содержать сообщение об ошибке.

    :param request: Входящий запрос.
    :return: JSON-ответ со статусом и опциональным сообщением об ошибке.
    """

    try:
        # Получаем сырой JSON без валидации Pydantic
        report = await request.json()

        # Валидация обязательных полей
        if not report:
            raise ValueError("Получен пустой отчет")

        # Дополнительная валидация структуры
        violation = None
        if "csp-report" in report:
            violation_data = report["csp-report"]
            # Если это dict, пробуем извлечь document_uri
            if isinstance(violation_data, dict):
                violation = violation_data
            else:
                # Если не dict, создаем базовую структуру
                violation = {
                    "document_uri": str(violation_data) if violation_data else "unknown"
                }
        elif "body" in report:
            violation_data = report["body"]
            # Если это dict, используем его
            if isinstance(violation_data, dict):
                violation = violation_data
            elif violation_data is not None:
                # Если не dict и не None, создаем базовую структуру
                violation = {"document_uri": str(violation_data)}
            else:
                # Если None, пропускаем (будет ошибка ниже)
                pass

        if not violation:
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
