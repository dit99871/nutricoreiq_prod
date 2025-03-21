""" """

from sqlalchemy.exc import SQLAlchemyError


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
