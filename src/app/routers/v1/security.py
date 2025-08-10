from fastapi import APIRouter
from fastapi.requests import Request
from fastapi.responses import ORJSONResponse

from src.app.core.logger import get_logger

router = APIRouter(
    tags=["Security"],
    default_response_class=ORJSONResponse,
)

log = get_logger("security_api")


@router.post("/csp-report")
async def csp_report(request: Request):
    """
    Endpoint to receive CSP violation reports.

    The endpoint accepts a JSON payload with the CSP violation report.

    Returns a JSON response with a status of "received" or "error". If the report
    is processed successfully, the status will be "received". If there is an error
    processing the report, the status will be "error" and the response will contain
    an error message.

    :param request: The incoming request.
    :return: A JSON response with a status and optional error message.
    """
    try:
        report = await request.json()
        log.warning(f"CSP violation detected: {report}")
        return {"status": "received"}
    except Exception as e:
        log.error(f"Error processing CSP report: {str(e)}")
        return {"status": "error", "message": str(e)}
