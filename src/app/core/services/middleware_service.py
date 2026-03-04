"""
Общие сервисы для мидлвари - централизация общей логики
"""

import json
import time
import uuid
from datetime import datetime
from typing import Any, Optional

from fastapi import Request, Response
from redis.asyncio import RedisError

from src.app.core.config import settings
from src.app.core.logger import get_logger
from src.app.core.redis import redis_client
from src.app.core.services.log_context_service import LogContextService
from src.app.core.utils.security import (
    generate_csrf_token,
    generate_csp_nonce,
)

logger = get_logger("middleware_service")


class CircuitBreaker:
    """Простой Circuit Breaker для защиты от каскадных сбоев"""

    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN

    async def call(self, func, *args, **kwargs):
        """Выполняет функцию с защитой circuit breaker"""

        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "HALF_OPEN"
            else:
                raise RedisError("Circuit breaker is OPEN")

        try:
            result = await func(*args, **kwargs)
            if self.state == "HALF_OPEN":
                self.state = "CLOSED"
                self.failure_count = 0
            return result

        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()

            if self.failure_count >= self.failure_threshold:
                self.state = "OPEN"
                logger.warning(
                    f"Circuit breaker OPEN due to {self.failure_count} failures"
                )

            raise e


class TracingService:
    """Unified tracing сервис для всех мидлвари"""

    @staticmethod
    def create_trace_id() -> str:
        """Создает уникальный trace ID"""

        return str(uuid.uuid4())

    @staticmethod
    def get_request_context(request: Request) -> dict[str, Any]:
        """Возвращает унифицированный контекст запроса"""

        return LogContextService.extract_context_from_request(request)

    @staticmethod
    def log_middleware_entry(
        middleware_name: str, context: dict[str, Any], extra_data: Optional[dict] = None
    ):
        """Логирует вход в мидлвари"""

        # объединяем контекст с дополнительными данными
        full_context = {**context, **(extra_data or {})}

        logger.info(
            f"[{middleware_name}] Entry",
            extra={
                **full_context,
                "context_string": LogContextService.format_context_string(full_context),
            },
        )

    @staticmethod
    def log_middleware_exit(
        middleware_name: str, context: dict[str, Any], extra_data: Optional[dict] = None
    ):
        """Логирует выход из мидлвари"""

        # объединяем контекст с дополнительными данными
        full_context = {**context, **(extra_data or {})}

        logger.info(
            f"[{middleware_name}] Exit",
            extra={
                **full_context,
                "context_string": LogContextService.format_context_string(full_context),
            },
        )

    @staticmethod
    def log_middleware_error(
        middleware_name: str,
        context: dict[str, Any],
        error: Exception,
        extra_data: Optional[dict] = None,
    ):
        """Логирует ошибку в мидлвари"""

        # объединяем контекст с дополнительными данными
        full_context = {
            **context,
            "middleware": middleware_name,
            "event": "error",
            "error_type": type(error).__name__,
            **(extra_data or {}),
        }

        logger.error(
            f"[{middleware_name}] Error: {str(error)}",
            extra={
                **full_context,
                "context_string": LogContextService.format_context_string(full_context),
            },
            exc_info=True,
        )


class SessionService:
    """Сервис для управления сессиями"""

    def __init__(self):
        self.redis_circuit_breaker = CircuitBreaker()
        self._session_cache: dict[str, dict] = {}
        self._cache_ttl = 300  # 5 минут

    async def get_session(self, session_id: str) -> Optional[dict]:
        """Получает сессию с кешированием"""

        # проверяем кеш
        if session_id in self._session_cache:
            cached_data = self._session_cache[session_id]
            if time.time() - cached_data["cached_at"] < self._cache_ttl:
                return cached_data["session"]

        try:
            # получаем из редиса с защитой circuit breaker
            session_data = await self.redis_circuit_breaker.call(
                redis_client.get, f"redis_session:{session_id}"
            )

            if session_data:
                session = json.loads(session_data)
                # кешируем
                self._session_cache[session_id] = {
                    "session": session,
                    "cached_at": time.time(),
                }
                return session

        except RedisError as e:
            logger.warning(f"Redis unavailable for session {session_id}: {e}")
            # пробуем вернуть из кеша если есть
            if session_id in self._session_cache:
                return self._session_cache[session_id]["session"]

        return None

    async def save_session(self, session_id: str, session: dict) -> None:
        """Сохраняет сессию в Redis и кеше"""

        try:
            await self.redis_circuit_breaker.call(
                redis_client.set,
                f"redis_session:{session_id}",
                json.dumps(session),
                ex=settings.redis.session_ttl,
            )

            # Обновляем кеш
            self._session_cache[session_id] = {
                "session": session,
                "cached_at": time.time(),
            }

        except RedisError as e:
            logger.warning(f"Failed to save session {session_id}: {e}")
            # сохраняем только в кеш
            self._session_cache[session_id] = {
                "session": session,
                "cached_at": time.time(),
            }

    def create_new_session(self, session_id: str) -> dict:
        """Создает новую сессию"""

        return {
            "redis_session_id": session_id,
            "created_at": datetime.now().isoformat(),
        }

    def ensure_csrf_token(self, session: dict) -> str:
        """Обеспечивает наличие CSRF токена в сессии"""

        csrf_token = session.get("csrf_token") or generate_csrf_token()
        session["csrf_token"] = csrf_token

        return csrf_token


class SecurityService:
    """Сервис для безопасности (CSRF, CSP)"""

    @staticmethod
    def generate_csp_nonce() -> str:
        """Генерирует CSP nonce"""

        return generate_csp_nonce()

    @staticmethod
    def build_csp_policy(csp_nonce: str) -> str:
        """Строит CSP политику"""
        policy = (
            "default-src 'self'; "
            f"script-src 'self' 'nonce-{csp_nonce}' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
            f"style-src 'self' 'nonce-{csp_nonce}' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
            f"style-src-attr 'nonce-{csp_nonce}'; "
            "font-src 'self' https://fonts.gstatic.com https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
            "img-src 'self' data: https:; "
            "connect-src 'self'; "
            "frame-src 'none'; "
            "object-src 'none'; "
            "form-action 'self'; "
            "upgrade-insecure-requests;"
        )

        # добавляем report-uri только в production
        if settings.env.env == "prod":
            policy += f"report-uri {settings.router.security}/csp-report;"

        return policy

    @staticmethod
    def validate_csrf_token(request: Request, session: dict) -> bool:
        """Валидирует CSRF токен"""
        # получаем токен из разных источников
        csrf_token = request.headers.get("X-CSRF-Token")
        if not csrf_token and request.method == "POST":
            # Для POST форм пробуем получить из формы
            try:
                form_data = request._form
                if form_data:
                    csrf_token = form_data.get("_csrf_token")
            except:
                pass

        if not csrf_token:

            return False

        # Проверяем совпадение с токеном в сессии и cookie
        csrf_token_cookie = request.cookies.get("csrf_token")
        session_csrf_token = session.get("csrf_token")

        return csrf_token == csrf_token_cookie and csrf_token == session_csrf_token

    @staticmethod
    def validate_origin(request: Request) -> bool:
        """Валидирует Origin/Referer"""

        origin = request.headers.get("origin") or request.headers.get("referer")
        if not origin:
            return True  # я некоторые браузеры не отправляют Origin

        return any(
            origin.startswith(allowed) for allowed in settings.cors.allow_origins
        )


class PrivacyService:
    """Сервис для проверки согласия на обработку данных"""

    def __init__(self):
        self._consent_cache: dict[str, Any] = {}
        self._cache_ttl = 600  # 10 минут

    async def check_user_consent(self, user_id: int, db_session) -> bool:
        """Проверяет согласие авторизованного пользователя с кешированием"""
        cache_key = f"user_{user_id}"

        # Проверяем кеш
        if cache_key in self._consent_cache:
            cached_time = self._consent_cache[f"{cache_key}_time"]
            if time.time() - cached_time < self._cache_ttl:
                return self._consent_cache[cache_key]

        try:
            from src.app.core.repo.privacy_consent import has_user_consent

            has_consent = await has_user_consent(db_session, user_id)

            # Кешируем результат
            self._consent_cache[cache_key] = has_consent
            self._consent_cache[f"{cache_key}_time"] = time.time()

            return has_consent

        except Exception as e:
            logger.warning(f"Failed to check user consent for {user_id}: {e}")
            return False

    def check_anonymous_consent(self, request: Request) -> bool:
        """Проверяет согласие анонимного пользователя"""
        # Проверяем заголовок
        consent_header = request.headers.get("X-Privacy-Consent")
        if consent_header:
            try:
                consent_data = json.loads(consent_header)
                return consent_data.get("personal_data", False)
            except json.JSONDecodeError:
                pass

        # Проверяем cookie
        consent_cookie = request.cookies.get("privacy_consent")
        if consent_cookie:
            try:
                consent_data = json.loads(consent_cookie)
                return consent_data.get("personal_data", False)
            except json.JSONDecodeError:
                pass

        return False


class ExceptionHandlingService:
    """Сервис для стандартизированной обработки ошибок"""

    @staticmethod
    def handle_middleware_exception(
        middleware_name: str,
        request: Request,
        exception: Exception,
        context: dict[str, Any],
    ) -> Response:
        """Стандартизированная обработка исключений в мидлвари"""

        # Логируем ошибку
        TracingService.log_middleware_error(middleware_name, context, exception)

        # Определяем тип ошибки и соответствующий ответ
        if isinstance(exception, RedisError):
            from fastapi import HTTPException, status

            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Сервис временно недоступен. Попробуйте позже.",
            )

        # Для остальных исключений пробрасываем дальше
        # чтобы обработали вышестоящие мидлвари или exception handlers
        raise exception


# Глобальные экземпляры сервисов
session_service = SessionService()
privacy_service = PrivacyService()
tracing_service = TracingService()
security_service = SecurityService()
exception_service = ExceptionHandlingService()
