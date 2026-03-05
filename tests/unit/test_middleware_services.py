"""
Юнит-тесты для сервисов мидлвари
"""

import pytest


class MockRequest:
    """Мок объекта Request для тестов"""
    def __init__(self, path="/", method="GET", headers=None, cookies=None):
        self.path = path
        self.method = method
        self.headers = headers or {}
        self.cookies = cookies or {}
        self.url = type('obj', (object,), {'path': path, 'query': '', '__str__': lambda self: f"http://testserver{path}"})()
        self.state = type('obj', (object,), {})()


class TestSessionService:
    """Тесты для Session Service"""
    
    def test_create_new_session(self):
        """Тест создания новой сессии"""
        from src.app.core.services.session_service import SessionService
        
        session_service = SessionService()
        session = session_service.create_new_session("session-123")
        
        assert session["redis_session_id"] == "session-123"
        assert "created_at" in session
    
    def test_ensure_csrf_token(self):
        """Тест обеспечения CSRF токена"""
        from src.app.core.services.session_service import SessionService
        
        session_service = SessionService()
        session = {}
        
        csrf_token = session_service.ensure_csrf_token(session)
        assert "csrf_token" in session
        assert len(session["csrf_token"]) == 64  # token_hex(32) = 64 hex chars
        
        # Повторный вызов должен вернуть тот же токен
        csrf_token2 = session_service.ensure_csrf_token(session)
        assert csrf_token == csrf_token2

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
