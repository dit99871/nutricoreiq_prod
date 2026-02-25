from pydantic import BaseModel, Field


class CSPReportResponse(BaseModel):
    """Схема ответа для CSP отчетов"""

    status: str = Field(..., pattern="^(received|error)$")
    message: str | None = None
