from redis.asyncio import Redis
from fastapi import Depends

from core.redis import get_redis


class RedisService:
    """ """

    def __init__(self, redis: Redis):
        self.redis = redis

    async def get_user_session(self, user_id: str):
        return await self.redis.get(f"user:{user_id}:session")


async def get_redis_service(redis: Redis = Depends(get_redis)):
    return RedisService(redis)
