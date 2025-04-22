from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Product, PendingProduct


async def add_pending(
    query: str,
    session: AsyncSession,
):
    """
    Adds a pending product to the database if it does not already exist.

    :param query: The name of the product to be added as pending.
    :param session: The database session used for executing queries.
    :return: None
    """
    # Проверяем существование в основных таблицах
    exists = await session.execute(select(Product).where(Product.title.ilike(query)))
    if exists.scalar():
        return None

    # Проверяем дубли в pending
    pending_exists = await session.execute(
        select(PendingProduct).where(PendingProduct.name.ilike(query))
    )
    if pending_exists.scalar():
        return None

    # Добавляем новый pending
    new_pending = PendingProduct(name=query)
    session.add(new_pending)
    try:
        await session.commit()
    except Exception as e:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error saving pending product: {str(e)}",
        )
