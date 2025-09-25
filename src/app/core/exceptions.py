from fastapi import HTTPException, status


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
