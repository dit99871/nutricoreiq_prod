from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.db.models import PendingProduct


async def check_pending_exists(
    session: AsyncSession,
    name: str,
) -> bool:
    """
    Check if a pending product with the given name exists in the database.

    :param session: AsyncSession
    :param name: str
    :return: bool
    """
    result = await session.execute(
        select(PendingProduct).where(PendingProduct.name.ilike(name))
    )
    return result.scalar() is not None


async def create_pending_product(
    session: AsyncSession,
    name: str,
) -> None:
    """
    Creates a new pending product in the database.

    :param session: AsyncSession
    :param name: str
    :return: None
    """
    new_pending = PendingProduct(name=name)
    session.add(new_pending)
    await session.commit()
