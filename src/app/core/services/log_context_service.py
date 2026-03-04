"""
Унифицированный сервис для форматирования контекста логов
"""

from typing import Any


class LogContextService:
    """
    Централизованный сервис для форматирования контекста запроса в логах.

    Обеспечивает единый формат и порядок полей для всех логов приложения.
    """

    # стандартизированный порядок полей для логов
    CONTEXT_FIELDS_ORDER = [
        "request_id",
        "method",
        "url",
        "client_ip",
        "user_agent",
        "status_code",
        "process_time_ms",
        "trace_id",
    ]

    @classmethod
    def format_context_string(cls, context: dict[str, Any]) -> str:
        """
        Форматирует контекст запроса в унифицированную строку.

        :param context: Словарь с контекстом запроса
        :return: Отформатированная строка контекста в формате:
                "request_id=xxx | method=POST | url=http://example.com | ..."
        """

        context_parts = []

        for field in cls.CONTEXT_FIELDS_ORDER:
            value = context.get(field)
            if value is not None and value != "unknown":
                context_parts.append(f"{field}={value}")

        return " | ".join(context_parts) if context_parts else ""

    @classmethod
    def extract_context_from_request(cls, request: Any) -> dict[str, Any]:
        """
        Извлекает контекст из FastAPI request объекта.

        :param request: FastAPI Request объект
        :return: Словарь с контекстом запроса
        """

        context = {}

        # извлекаем атрибуты из request.state
        state_fields = ["trace_id", "request_id", "client_ip", "effective_url"]
        for field in state_fields:
            value = getattr(request.state, field, None)
            if value:
                context[field] = value

        # извлекаем данные из request
        if hasattr(request, "method"):
            context["method"] = request.method

        if hasattr(request, "url"):
            context["url"] = str(getattr(request.state, "effective_url", request.url))

        if hasattr(request, "headers"):
            context["user_agent"] = request.headers.get("user-agent", "unknown")

        return context
