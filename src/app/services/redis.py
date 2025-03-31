import datetime as dt

from redis.asyncio import Redis, RedisError
from fastapi import Depends, HTTPException, status

from core.logger import get_logger
from core.redis import get_redis
from utils.security import generate_hash_token

log = get_logger("redis_service")


class RedisService:
    """ """

    def __init__(self, redis: Redis):
        self.redis = redis

    async def get_user_session(self, user_id: str):
        return await self.redis.get(f"user:{user_id}:session")


async def get_redis_service(redis: Redis = Depends(get_redis)):
    return RedisService(redis)


async def set_in_redis(
    user_id: int,
    jwt: str,
    exp: dt.timedelta,
    redis: Redis = Depends(get_redis),
):
    try:
        token_hash = generate_hash_token(jwt)
        await redis.set(
            f"refresh_token:{user_id}:{token_hash}",
            "valid",
            ex=exp,
        )
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