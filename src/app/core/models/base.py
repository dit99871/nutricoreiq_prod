"""Базовые сущности SQLAlchemy (DeclarativeBase) и общая мета-конфигурация."""

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase, declared_attr

from src.app.core.config import settings
from src.app.core.utils import camel_case_to_snake_case


class Base(DeclarativeBase):
    """Базовый класс для всех ORM-моделей приложения."""

    __abstract__ = True

    metadata = MetaData(
        naming_convention=settings.db.naming_convention,
    )

    @declared_attr.directive
    def __tablename__(self) -> str:
        """Автоматически формирует имя таблицы из имени класса."""

        return f"{camel_case_to_snake_case(self.__name__)}s"
