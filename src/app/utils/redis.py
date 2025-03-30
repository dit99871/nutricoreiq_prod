from fastapi import Depends
from redis.asyncio import Redis

from services.redis_service import get_redis_service


async def validate_refresh_jwt(
    user_id: str,
    refresh_token: str,
    redis: Redis = Depends(get_redis_service),
) -> bool:
    # Проверяем, не отозван ли токен
    token_key = f"refresh_token:{user_id}:{refresh_token}"
    exists = await redis.exists(token_key)
    return exists == 1


async def revoke_refresh_token(
    user_id: str,
    refresh_token: str,
    redis: Redis = Depends(get_redis_service),
) -> None:
    token_key = f"refresh_token:{user_id}:{refresh_token}"
    await redis.delete(token_key)


async def revoke_all_refresh_tokens(
    user_id: str,
    redis: Redis = Depends(get_redis_service),
) -> None:
    # Находим все refresh токены пользователя и удаляем их
    keys = await redis.keys(f"refresh_token:{user_id}:*")
    if keys:
        await redis.delete(*keys)
