from datetime import timedelta

from redis.asyncio import Redis
from fastapi import Depends

from core.redis import get_redis
from utils.security import generate_hash_token


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
    exp: timedelta,
    redis: Redis = Depends(get_redis),
):
    token_hash = generate_hash_token(jwt)
    await redis.set(
        f"refresh_token:{user_id}:{token_hash}",
        "valid",
        ex=exp,
    )
