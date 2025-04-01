from datetime import datetime

from fastapi import Depends, HTTPException
from redis.asyncio import Redis

from core.logger import get_logger
from core.redis import get_redis
from services.redis import add_to_blacklist
from utils.auth import decode_jwt
from utils.security import generate_hash_token

log = get_logger("redis_utils")


async def is_token_blacklisted(
    redis: Redis,
    token: str,
) -> bool:
    """
    Checks whether a given token is blacklisted.

    This function takes a given token, hashes it with a salt, and checks whether
    the hashed token exists in the Redis "blacklist:refresh" key. If the hashed
    token is found, it returns True, indicating that the token is blacklisted.
    Otherwise, it returns False.

    :param redis: The Redis instance to be used for checking the blacklist.
    :param token: The token to be checked against the blacklist.
    :return: A boolean indicating whether the token is blacklisted.
    """
    hashed_token = generate_hash_token(token)
    return await redis.exists(f"blacklist:refresh:{hashed_token}") == 1


async def validate_refresh_jwt(
    uid: str,
    refresh_token: str,
    redis: Redis,
) -> bool:
    try:
        token_hash = generate_hash_token(refresh_token)

        # 1. Проверяем черный список
        if await is_token_blacklisted(redis, token_hash):
            log.error("Refresh token is blacklisted")
            return False

        # 2. Проверяем активные токены
        token_key = f"refresh_token:{uid}:{token_hash}"
        return await redis.exists(token_key) == 1
    except HTTPException as e:
        raise e


async def revoke_refresh_token(
    user_id: int,
    refresh_token: str,
    redis: Redis,
) -> None:
    token_hash = generate_hash_token(refresh_token)

    # 1. Удаляем из активных
    token_key = f"refresh_token:{user_id}:{token_hash}"
    await redis.delete(token_key)

    # 2. Добавляем в черный список
    try:
        payload = decode_jwt(refresh_token)
        expire_at = datetime.fromtimestamp(payload["exp"])
        await add_to_blacklist(redis, token_hash, user_id, expire_at)
    except HTTPException as e:
        raise e


async def revoke_all_refresh_tokens(
    user_id: str,
    redis: Redis = Depends(get_redis),
) -> None:
    # Находим все refresh токены пользователя и удаляем их
    keys = await redis.keys(f"refresh_token:{user_id}:*")
    if keys:
        await redis.delete(*keys)
