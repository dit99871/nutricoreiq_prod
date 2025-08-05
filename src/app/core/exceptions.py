""" """

from sqlalchemy.exc import SQLAlchemyError
from fastapi import HTTPException, status


class ExpiredTokenException(HTTPException):
    """
    Исключение для случаев, когда токен истек
    """

    def __init__(self, detail: str = "Token has expired"):

        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
        )


class AppError(Exception):
    """Базовое исключение для приложения."""

    pass


class NotFoundError(AppError):
    """Исключение для случаев, когда данные не найдены."""

    pass


class ValidationError(AppError):
    """Исключение для ошибок валидации."""

    pass


class DatabaseError(SQLAlchemyError, AppError):
    """Исключение для ошибок базы данных."""

    pass
