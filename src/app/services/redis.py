import datetime as dt

from redis.asyncio import Redis, RedisError
from fastapi import Depends, HTTPException, status

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
            await redis.set(
                f"refresh_token:{uid}:{token_hash}",
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


async def add_to_blacklist(
    redis: Redis,
    token: str,
    user_id: int,
    expire_at: dt.datetime,
):
    remaining_time = (expire_at - dt.datetime.now(dt.UTC)).total_seconds()
    try:
        if remaining_time > 0:
            token_hash = generate_hash_token(token)
            await redis.set(
                f"blacklist:refresh:{token_hash}",
                user_id,
                ex=int(remaining_time),
            )
    except RedisError as e:
        log.error("Redis error adding refresh token to blacklist: %s", e)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Redis error adding refresh token to blacklist: {str(e)}",
        )
