"""Репозиторий для очереди ожидающих добавления продуктов."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.core.exceptions import ValidationError, ConflictError
from src.app.core.models import PendingProduct


async def pending_product_exists(
    session: AsyncSession,
    name: str,
) -> bool:
    """Проверяет, существует ли ожидающий продукт с данным именем."""

    normalized_name = name.strip()
    if not normalized_name:
        return False

    result = await session.execute(
        select(PendingProduct).where(
            func.lower(PendingProduct.name) == normalized_name.lower()
        )
    )

    return result.scalar_one_or_none() is not None


async def create_pending_product(
    session: AsyncSession,
    name: str,
    *,
    raise_if_exists: bool = True,
) -> bool:
    """
    Создает продукт в очереди на добавление. Возвращает True, если продукт был создан.

    Если ``raise_if_exists`` == True, вызывает ConflictError, когда продукт уже находится в очереди.
    """

    normalized_name = name.strip()
    if not normalized_name:
        raise ValidationError("Название продукта не может быть пустым", field="name")

    if await pending_product_exists(session, normalized_name):
        if raise_if_exists:
            raise ConflictError("Продукт уже в очереди на добавление")
        return False

    new_pending = PendingProduct(name=normalized_name)
    session.add(new_pending)
    await session.commit()

    return True
