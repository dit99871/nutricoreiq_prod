"""
Унифицированный сервис для форматирования контекста логов
"""

import uuid
from typing import Any

from fastapi import Request

from src.app.core.utils.network import get_client_ip, get_scheme_and_host


class LogContextService:
    """
    Централизованный сервис для форматирования контекста запроса в логах.

    Обеспечивает единый формат и порядок полей для всех логов приложения.
    """

    # стандартизированный порядок полей для логов
    CONTEXT_FIELDS_ORDER = [
        "status",
        "ip",
        "ua",
        "ms",
        "request_id",
        "trace_id",
    ]

    @classmethod
    def format_context_string(cls, context: dict[str, Any]) -> str:
        """
        Форматирует контекст запроса в унифицированную строку.

        Используется совместно с format_request_line — метод и путь
        добавляются отдельно перед контекстом.

        :param context: Словарь с контекстом запроса
        :return: Отформатированная строка контекста в формате:
                "status=200 | ip=1.2.3.4 | ua=Chrome/120 | ms=4.67 | request_id=... | trace_id=..."
        """

        context_parts = []

        for field in cls.CONTEXT_FIELDS_ORDER:
            value = context.get(field)
            if value is not None and value != "unknown":
                context_parts.append(f"{field}={value}")

        return " | ".join(context_parts) if context_parts else ""

    @classmethod
    def setup_request_ids(cls, request: Request) -> None:
        """
        Устанавливает trace_id и request_id для запроса.

        :param request: FastAPI Request объект
        """

        # устанавливаем trace_id если его нет
        if not hasattr(request.state, "trace_id"):
            request.state.trace_id = str(uuid.uuid4())

        # устанавливаем request_id из заголовка или генерируем новый
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id

    @classmethod
    def setup_request_context(
        cls, request: Request, trusted_proxies: list[str] | None = None
    ) -> None:
        """
        Устанавливает атрибуты контекста в request.state.

        :param request: FastAPI Request объект
        :param trusted_proxies: Список доверенных прокси
        """

        # устанавливаем id
        cls.setup_request_ids(request)

        # получаем ip клиента
        client_ip = getattr(request.state, "client_ip", None) or get_client_ip(
            request, trusted_proxies=trusted_proxies or []
        )
        request.state.client_ip = client_ip

        # получаем схему и хост
        scheme, host = get_scheme_and_host(
            request, trusted_proxies=trusted_proxies or []
        )
        request.state.scheme = scheme
        request.state.host = host
        request.state.effective_url = request.url.replace(scheme=scheme, netloc=host)

    @classmethod
    def ensure_context_fields(cls, context: dict[str, Any]) -> dict[str, Any]:
        """
        Гарантирует наличие всех полей контекста с fallback значениями.

        :param context: Словарь с контекстом запроса
        :return: Контекст с гарантированно заполненными полями
        """

        ensured_context = context.copy()

        # обязательные поля с fallback значениями
        required_fields = {
            "status": "unknown",
            "ip": "unknown",
            "ua": "unknown",
            "ms": None,
            "request_id": "unknown",
            "trace_id": "unknown",
        }

        for field, fallback in required_fields.items():
            if field not in ensured_context or ensured_context[field] is None:
                ensured_context[field] = fallback

        return ensured_context

    @classmethod
    def format_request_line(cls, request: Request) -> str:
        """Возвращает строку вида 'GET /path'"""
        return f"{request.method} {request.url.path}"

    @classmethod
    def validate_context(cls, context: dict[str, Any]) -> dict[str, Any]:
        """
        Валидирует контекст и добавляет fallback значения.

        :param context: Словарь с контекстом запроса
        :return: Валидированный контекст
        """

        validated_context = cls.ensure_context_fields(context)

        # дополнительная валидация критических полей
        critical_fields = ["request_id", "trace_id"]
        for field in critical_fields:
            if (
                not validated_context.get(field)
                or validated_context[field] == "unknown"
            ):
                # для критических полей генерируем новые значения
                if field == "request_id":
                    validated_context[field] = str(uuid.uuid4())
                elif field == "trace_id":
                    validated_context[field] = str(uuid.uuid4())

        return validated_context

    @classmethod
    def get_safe_context(cls, request: Request) -> dict[str, Any]:
        """
        Извлекает и валидирует контекст из запроса.

        :param request: FastAPI Request объект
        :return: Валидированный словарь с контекстом запроса
        """

        context = cls.extract_context_from_request(request)
        return cls.validate_context(context)

    @classmethod
    def extract_context_from_request(cls, request: Any) -> dict[str, Any]:
        """
        Извлекает контекст из FastAPI request объекта.

        :param request: FastAPI Request объект
        :return: Словарь с контекстом запроса
        """

        context = {}

        # извлекаем атрибуты из request.state
        state_fields = {
            "client_ip": "ip",
            "effective_url": "url",
            "trace_id": "trace_id",
            "request_id": "request_id",
        }
        for state_key, context_key in state_fields.items():
            value = getattr(request.state, state_key, None)
            if value:
                context[context_key] = value

        # извлекаем данные из request
        if hasattr(request, "method"):
            context["method"] = request.method

        if hasattr(request, "url"):
            context["url"] = getattr(request.state, "effective_url", None) or str(
                request.url
            )

        if hasattr(request, "headers"):
            context["ua"] = request.headers.get("user-agent", "unknown")

        # добавляем status_code и process_time_ms если доступны
        if hasattr(request.state, "status_code"):
            context["status"] = request.state.status_code

        if hasattr(request.state, "process_time_ms"):
            context["ms"] = request.state.process_time_ms

        return context
