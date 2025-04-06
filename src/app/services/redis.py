import datetime as dt
import time

from redis.asyncio import RedisError, Redis
from fastapi import HTTPException, status, Depends

from core.logger import get_logger
from core.redis import get_redis
from utils.security import generate_hash_token

log = get_logger("redis_service")


async def add_refresh_to_redis(
    uid: str,
    jwt: str,
    exp: dt.timedelta,
):
    try:
        async for redis in get_redis():
            token_hash = generate_hash_token(jwt)
            # Check the number of tokens for the uid
            keys = await redis.keys(f"refresh_token:{uid}:*")
            if len(keys) >= 4:
                # Find the oldest token and delete it
                oldest_key = min(keys, key=lambda k: int(k.rsplit(":", 1)[-1]))
                await redis.delete(oldest_key)
            timestamp = time.time_ns()  # Get current timestamp
            await redis.set(
                f"refresh_token:{uid}:{token_hash}:{timestamp}",
                "valid",
                ex=exp,
            )
            log.info("Refresh token added to redis")
    except RedisError as e:
        log.error("Redis error adding refresh token: %s", e)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Redis error adding refresh token: {str(e)}",
        )


async def validate_refresh_jwt(
    uid: str,
    refresh_token: str,
    redis: Redis,
) -> bool:
    try:
        token_hash = generate_hash_token(refresh_token)
        token_key = f"refresh_token:{uid}:{token_hash}:*"

        return await redis.exists(token_key) == 1

    except HTTPException as e:
        raise e


async def revoke_refresh_token(
    uid: str,
    refresh_token: str,
    redis: Redis,
) -> None:
    token_hash = generate_hash_token(refresh_token)
    token_key = f"refresh_token:{uid}:{token_hash}"
    await redis.delete(token_key)
    log.info("Refresh token revoked")


async def revoke_all_refresh_tokens(
    uid: str,
) -> None:
    # Находим все refresh токены пользователя и удаляем их
    try:
        async for redis in get_redis():
            keys = await redis.keys(f"refresh_token:{uid}:*")
            if keys:
                await redis.delete(*keys)
                log.info("All refresh tokens revoked")
    except RedisError as e:
        log.error("Redis error revoking refresh tokens: %s", e)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Redis error revoking refresh tokens: {str(e)}",
        )
