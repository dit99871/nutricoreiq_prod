import datetime as dt
import time

from redis.asyncio import RedisError, Redis
from fastapi import HTTPException, status

from src.app.core.logger import get_logger
from src.app.core.redis import get_redis
from src.app.utils.security import generate_hash_token

log = get_logger("redis_service")


async def add_refresh_to_redis(
    uid: str,
    jwt: str,
    exp: dt.timedelta,
) -> None:
    """
    Adds a refresh token to the Redis database for a given user.

    This function generates a hash of the provided JWT and stores it in Redis
    with an expiration time. It ensures that no more than four tokens exist
    for the user by deleting the oldest token if necessary. The token is stored
    with a unique timestamp to maintain the order of creation.

    :param uid: The user ID for which the refresh token is to be added.
    :param jwt: The JSON Web Token to be added.
    :param exp: The expiration duration for the token.
    :raises HTTPException: If there is an error interacting with Redis.
    """
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
    """
    Validates a refresh token for a given user.

    Validates a refresh token from the Redis database for a given user ID and
    refresh token. The token is hashed and the corresponding key in Redis is
    checked for existence. If the token is invalid, has expired, or does not
    exist, raises an HTTPException with a 401 status code and an appropriate
    error message.

    :param uid: The user ID for which to validate the refresh token.
    :param refresh_token: The refresh token to be validated.
    :param redis: The Redis client to use for the query.
    :raises HTTPException: If the token is invalid, has expired, or does not
                           exist.
    :return: True if the token is valid, False otherwise.
    """
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
    """
    Revokes a refresh token for a given user.

    Revokes a refresh token from the Redis database for a given user ID and
    refresh token. The token is hashed and the corresponding key in Redis is
    deleted. The function logs a message when the token is successfully revoked.

    :param uid: The user ID for which to revoke the refresh token.
    :param refresh_token: The refresh token to be revoked.
    :param redis: The Redis client to use for the query.
    :return: None
    """
    token_hash = generate_hash_token(refresh_token)
    token_keys = await redis.keys(f"refresh_token:{uid}:{token_hash}:*")
    if token_keys:
        await redis.delete(*token_keys)
        log.info("Refresh token revoked")


async def revoke_all_refresh_tokens(
    uid: str,
) -> None:
    """
    Revoke all refresh tokens for a given user.

    This function revokes all refresh tokens for a given user id by deleting the
    corresponding keys from Redis. If there are any Redis errors during the process,
    it raises an HTTPException with a 401 status code.

    :param uid: The user id for which to revoke all refresh tokens.
    :type uid: str
    """
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
