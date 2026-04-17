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
        self.url = type(
            "obj",
            (object,),
            {
                "path": path,
                "query": "",
                "__str__": lambda self: f"http://testserver{path}",
            },
        )()
        self.state = type("obj", (object,), {})()


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


class TestCSRFExceptions:
    """Тесты для CSRF исключений"""

    def test_csrf_domain_error_creation(self):
        """Тест создания CSRFDomainError"""
        from src.app.core.exceptions import CSRFDomainError

        error = CSRFDomainError()
        assert error.status_code == 403
        assert error.error_code == "CSRF_DOMAIN_ERROR"
        assert "Нет доступа" in error.message

        # Тест с кастомным сообщением
        custom_error = CSRFDomainError("Custom domain error")
        assert custom_error.message == "Custom domain error"

    def test_csrf_session_expired_error_creation(self):
        """Тест создания CSRFSessionExpiredError"""
        from src.app.core.exceptions import CSRFSessionExpiredError

        error = CSRFSessionExpiredError()
        assert error.status_code == 403
        assert error.error_code == "CSRF_SESSION_EXPIRED_ERROR"
        assert "Время сессии истекло" in error.message

        # Тест с кастомным сообщением
        custom_error = CSRFSessionExpiredError("Custom session expired")
        assert custom_error.message == "Custom session expired"

    def test_csrf_token_error_creation(self):
        """Тест создания CSRFTokenError"""
        from src.app.core.exceptions import CSRFTokenError

        error = CSRFTokenError()
        assert error.status_code == 403
        assert error.error_code == "CSRF_TOKEN_ERROR"
        assert "Нет доступа" in error.message

        # Тест с кастомным сообщением
        custom_error = CSRFTokenError("Custom token error")
        assert custom_error.message == "Custom token error"

    def test_csrf_errors_inherit_from_base_application_error(self):
        """Тест на то, что CSRF ошибки наследуются от BaseApplicationError"""
        from src.app.core.exceptions import (
            BaseApplicationError,
            CSRFDomainError,
            CSRFSessionExpiredError,
            CSRFTokenError,
        )

        assert issubclass(CSRFDomainError, BaseApplicationError)
        assert issubclass(CSRFSessionExpiredError, BaseApplicationError)
        assert issubclass(CSRFTokenError, BaseApplicationError)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
