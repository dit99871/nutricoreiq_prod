from fastapi import HTTPException, status
from typing import Any, Optional


class ExpiredTokenException(HTTPException):
    """
    Исключение для случаев, когда токен истек
    """

    def __init__(
        self,
        detail: str = "Срок действия токена истек. Пожалуйста, войдите заново.",
    ):

        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
        )


class UserServiceError(Exception):
    """Базовый класс для ошибок сервиса пользователей"""

    pass


class UserAlreadyExistsError(UserServiceError):
    """Ошибка при попытке создать пользователя, который уже существует"""

    status_code = status.HTTP_400_BAD_REQUEST

    def __init__(self, message: str = "Пользователь с такими данными уже существует"):
        self.detail = message
        super().__init__(self.detail)


class BaseApplicationError(Exception):
    """Базовый класс для всех ошибок приложения"""

    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_code: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}
        super().__init__(message)


class ValidationError(BaseApplicationError):
    """Ошибка валидации данных"""

    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="VALIDATION_ERROR",
            details={**(details or {}), **({"field": field} if field else {})},
        )


class AuthenticationError(BaseApplicationError):
    """Ошибка аутентификации"""

    def __init__(self, message: str = "Ошибка аутентификации"):
        super().__init__(
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code="AUTHENTICATION_ERROR",
        )


class AuthorizationError(BaseApplicationError):
    """Ошибка авторизации"""

    def __init__(self, message: str = "Доступ запрещен"):
        super().__init__(
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
            error_code="AUTHORIZATION_ERROR",
        )


class NotFoundError(BaseApplicationError):
    """Ресурс не найден"""

    def __init__(
        self, message: str = "Ресурс не найден", resource_type: Optional[str] = None
    ):
        super().__init__(
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="NOT_FOUND_ERROR",
            details={"resource_type": resource_type} if resource_type else {},
        )


class ConflictError(BaseApplicationError):
    """Конфликт данных"""

    def __init__(
        self, message: str = "Конфликт данных", details: Optional[dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            status_code=status.HTTP_409_CONFLICT,
            error_code="CONFLICT_ERROR",
            details=details or {},
        )


class DatabaseError(BaseApplicationError):
    """Ошибка базы данных"""

    def __init__(
        self,
        message: str = "Ошибка базы данных",
        original_error: Optional[Exception] = None,
    ):
        super().__init__(
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="DATABASE_ERROR",
            details={"original_error": str(original_error)} if original_error else {},
        )


class ExternalServiceError(BaseApplicationError):
    """Ошибка внешнего сервиса"""

    def __init__(
        self,
        message: str,
        service_name: str,
        original_error: Optional[Exception] = None,
    ):
        super().__init__(
            message=message,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            error_code="EXTERNAL_SERVICE_ERROR",
            details={
                "service": service_name,
                "original_error": str(original_error) if original_error else None,
            },
        )


class CSRFDomainError(BaseApplicationError):
    """Ошибка CSRF - недопустимый домен"""

    def __init__(
        self,
        message: str = "Нет доступа. Пожалуйста, убедитесь, что вы обращаетесь с авторизованного домена.",
    ):
        super().__init__(
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
            error_code="CSRF_DOMAIN_ERROR",
        )


class CSRFSessionExpiredError(BaseApplicationError):
    """Ошибка CSRF - сессия истекла"""

    def __init__(
        self, message: str = "Время сессии истекло. Пожалуйста, войдите снова."
    ):
        super().__init__(
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
            error_code="CSRF_SESSION_EXPIRED_ERROR",
        )


class CSRFTokenError(BaseApplicationError):
    """Ошибка CSRF - недействительный токен"""

    def __init__(
        self,
        message: str = "Нет доступа. Пожалуйста, обновите страницу и попробуйте ещё раз.",
    ):
        super().__init__(
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
            error_code="CSRF_TOKEN_ERROR",
        )
