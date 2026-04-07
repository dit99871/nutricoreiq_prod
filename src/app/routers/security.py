from fastapi import APIRouter
from fastapi.requests import Request
from fastapi.responses import JSONResponse

from src.app.core.logger import get_logger
from src.app.core.schemas.security import CSPReportResponse
from src.app.core.services.csp_service import CSPReportService

router = APIRouter(
    tags=["Security"],
    default_response_class=JSONResponse,
)

log = get_logger("security_router")


@router.post("/csp-report")
async def csp_report(request: Request) -> CSPReportResponse:
    """
    Эндпоинт для получения отчетов о нарушениях CSP.

    Эндпоинт принимает JSON-полезную нагрузку с отчетом о нарушении CSP.
    Обрабатывает отчет через CSPReportService и логирует нарушения.

    Возвращает JSON-ответ со статусом "received" или "error". Если отчет
    успешно обработан, статус будет "received". При ошибке
    обработки статус будет "error" и ответ будет содержать сообщение об ошибке.

    :param request: Входящий запрос.
    :return: JSON-ответ со статусом и опциональным сообщением об ошибке.
    """

    try:
        # получаем сырой json
        report = await request.json()

        # обрабатываем отчет через сервис
        effective_directive, doc_uri, blocked_uri = CSPReportService.process_report(
            report
        )

        # логируем нарушение
        log.warning(
            "Обнаружено нарушение CSP: %s с %s - заблокировано: %s",
            effective_directive,
            doc_uri,
            blocked_uri,
        )

        return CSPReportResponse(status="received")

    except Exception as e:
        log.error("Ошибка обработки CSP отчета: %s", e)
        return CSPReportResponse(status="error", message=str(e))
