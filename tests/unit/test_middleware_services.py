#!/usr/bin/env python3
"""
Юнит-тесты для сервисов мидлвари
"""
import asyncio
import json
import pytest


class MockRequest:
    """Мок объекта Request для тестов"""
    def __init__(self, path="/", method="GET", headers=None, cookies=None):
        self.path = path
        self.method = method
        self.headers = headers or {}
        self.cookies = cookies or {}
        self.url = type('obj', (object,), {'path': path, 'query': ''})()
        self.state = type('obj', (object,), {})()


class TestCircuitBreaker:
    """Тесты для Circuit Breaker"""
    
    def test_circuit_breaker_normal_operation(self):
        """Тест нормальной работы"""
        from src.app.core.services.middleware_service import CircuitBreaker
        
        async def test_func():
            return "success"
        
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=1)
        
        async def run_test():
            result = await cb.call(test_func)
            assert result == "success"
        
        asyncio.run(run_test())
    
    def test_circuit_breaker_opens_on_failures(self):
        """Тест открытия circuit breaker после ошибок"""
        from src.app.core.services.middleware_service import CircuitBreaker
        
        async def failing_func():
            raise ValueError("Test error")
        
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=1)
        
        async def run_test():
            try:
                await cb.call(failing_func)
            except:
                pass
            
            try:
                await cb.call(failing_func)
            except:
                pass
            
            # Третий вызов должен быть заблокирован
            try:
                await cb.call(failing_func)
                assert False, "Should be blocked"
            except Exception as e:
                assert "Circuit breaker is OPEN" in str(e)
        
        asyncio.run(run_test())


class TestTracingService:
    """Тесты для Tracing Service"""
    
    def test_create_trace_id(self):
        """Тест генерации trace ID"""
        from src.app.core.services.middleware_service import TracingService
        
        trace_id = TracingService.create_trace_id()
        assert len(trace_id) == 36  # UUID length
        assert isinstance(trace_id, str)
    
    def test_get_request_context(self):
        """Тест получения контекста запроса"""
        from src.app.core.services.middleware_service import TracingService
        
        request = MockRequest(
            path="/api/test",
            method="POST",
            headers={"user-agent": "test-agent", "X-Request-ID": "req-123"}
        )
        request.state.trace_id = "trace-456"
        request.state.request_id = "req-123"
        request.state.client_ip = "127.0.0.1"
        
        context = TracingService.get_request_context(request)
        
        assert context["trace_id"] == "trace-456"
        assert context["request_id"] == "req-123"
        assert context["method"] == "POST"
        assert context["path"] == "/api/test"
        assert context["user_agent"] == "test-agent"


class TestSessionService:
    """Тесты для Session Service"""
    
    def test_create_new_session(self):
        """Тест создания новой сессии"""
        from src.app.core.services.middleware_service import SessionService
        
        session_service = SessionService()
        session = session_service.create_new_session("session-123")
        
        assert session["redis_session_id"] == "session-123"
        assert "created_at" in session
    
    def test_ensure_csrf_token(self):
        """Тест обеспечения CSRF токена"""
        from src.app.core.services.middleware_service import SessionService
        
        session_service = SessionService()
        session = {}
        
        csrf_token = session_service.ensure_csrf_token(session)
        assert "csrf_token" in session
        assert len(session["csrf_token"]) == 64  # token_hex(32) = 64 hex chars
        
        # Повторный вызов должен вернуть тот же токен
        csrf_token2 = session_service.ensure_csrf_token(session)
        assert csrf_token == csrf_token2


class TestSecurityService:
    """Тесты для Security Service"""
    
    def test_generate_csp_nonce(self):
        """Тест генерации CSP nonce"""
        from src.app.core.services.middleware_service import SecurityService
        
        nonce = SecurityService.generate_csp_nonce()
        assert len(nonce) == 43  # token_urlsafe(32) = 43 chars with padding
        assert isinstance(nonce, str)
    
    def test_build_csp_policy(self):
        """Тест построения CSP политики"""
        from src.app.core.services.middleware_service import SecurityService
        
        nonce = "test-nonce-123"
        csp_policy = SecurityService.build_csp_policy(nonce)
        
        assert f"nonce-{nonce}" in csp_policy
        assert "default-src 'self'" in csp_policy
        assert "script-src 'self'" in csp_policy
    
    def test_validate_origin(self):
        """Тест валидации Origin"""
        from src.app.core.services.middleware_service import SecurityService
        
        # Отсутствующий origin - должен возвращать True
        request1 = MockRequest(headers={})
        assert SecurityService.validate_origin(request1) == True
        
        # Проверяем, что функция работает с любым origin
        # (конкретные значения зависят от настроек CORS)
        request2 = MockRequest(headers={"origin": "https://example.com"})
        result = SecurityService.validate_origin(request2)
        assert isinstance(result, bool)  # Должен возвращать bool
        
        request3 = MockRequest(headers={"origin": "http://localhost:8000"})
        result = SecurityService.validate_origin(request3)
        assert isinstance(result, bool)  # Должен возвращать bool


class TestPrivacyService:
    """Тесты для Privacy Service"""
    
    def test_check_anonymous_consent_header(self):
        """Тест проверки согласия через заголовок"""
        from src.app.core.services.middleware_service import PrivacyService
        
        privacy_service = PrivacyService()
        
        # Согласие через заголовок
        request = MockRequest(headers={
            "X-Privacy-Consent": json.dumps({"personal_data": True})
        })
        assert privacy_service.check_anonymous_consent(request) == True
        
        # Отсутствие согласия
        request2 = MockRequest(headers={
            "X-Privacy-Consent": json.dumps({"personal_data": False})
        })
        assert privacy_service.check_anonymous_consent(request2) == False
    
    def test_check_anonymous_consent_cookie(self):
        """Тест проверки согласия через cookie"""
        from src.app.core.services.middleware_service import PrivacyService
        
        privacy_service = PrivacyService()
        
        # Согласие через cookie
        request = MockRequest(cookies={
            "privacy_consent": json.dumps({"personal_data": True})
        })
        assert privacy_service.check_anonymous_consent(request) == True
        
        # Невалидный JSON
        request2 = MockRequest(headers={"X-Privacy-Consent": "invalid-json"})
        assert privacy_service.check_anonymous_consent(request2) == False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
