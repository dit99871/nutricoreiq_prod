from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.core.models import PendingProduct


async def pending_product_exists(
    session: AsyncSession,
    name: str,
) -> bool:
    """Check if a pending product with the given name already exists."""

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
    Create a new pending product. Returns True if the product was created.

    If ``raise_if_exists`` is True, raises HTTP 400 when the product is already queued.
    """

    normalized_name = name.strip()
    if not normalized_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "Название продукта не может быть пустым"},
        )

    if await pending_product_exists(session, normalized_name):
        if raise_if_exists:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"message": "Продукт уже в очереди на добавление"},
            )
        return False

    new_pending = PendingProduct(name=normalized_name)
    session.add(new_pending)
    await session.commit()

    return True
