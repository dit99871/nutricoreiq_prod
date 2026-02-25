from typing import Any
from pydantic import BaseModel, Field


class CSPBlockedURI(BaseModel):
    """Схема для данных о нарушении CSP"""

    blocked_uri: str | None = None
    document_uri: str | None = None
    effective_directive: str | None = None
    original_policy: str | None = None
    referrer: str | None = None
    sample: str | None = None
    source_file: str | None = None
    line_number: int | None = None
    column_number: int | None = None
    status_code: int | None = None


class CSPViolationReport(BaseModel):
    """Схема отчета о нарушении CSP"""

    csp_report: CSPBlockedURI | None = None

    # Для legacy формата - принимаем абсолютно любой тип без валидации
    body: Any = None

    class Config:
        extra = "forbid"  # Запрещаем лишние поля


class CSPReportResponse(BaseModel):
    """Схема ответа для CSP отчетов"""

    status: str = Field(..., pattern="^(received|error)$")
    message: str | None = None
