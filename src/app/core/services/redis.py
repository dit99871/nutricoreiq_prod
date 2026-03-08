import datetime as dt
import time

from fastapi import Request
from redis.asyncio import Redis, RedisError

from src.app.core.exceptions import ExternalServiceError
from src.app.core.logger import get_logger
from src.app.core.redis import get_redis_service
from src.app.core.utils.security import generate_hash_token

log = get_logger("redis_service")


async def _scan_keys(redis: Redis, pattern: str, count: int = 100) -> list[str]:
    """Неблокирующий помощник для сканирования ключей с использованием SCAN.

    :param redis: подключение к Redis
    :param pattern: шаблон в стиле glob
    :param count: подсказка о размере страницы сканирования
    :return: список ключей, соответствующих шаблону
    """

    keys: list[str] = []
    async for k in redis.scan_iter(match=pattern, count=count):
        keys.append(k)
    return keys


async def add_refresh_jwt_to_redis(
    uid: str,
    jwt: str,
    exp: dt.timedelta,
) -> None:
    """
    Добавляет refresh токен в базу данных Redis для указанного пользователя.

    Эта функция генерирует хеш предоставленного JWT и сохраняет его в Redis
    со сроком действия. Обеспечивает, чтобы у пользователя было не более четырех токенов,
    удаляя самый старый токен при необходимости. Токен сохраняется
    с уникальной временной меткой для поддержания порядка создания.

    :param uid: ID пользователя, для которого добавляется refresh токен.
    :param jwt: JSON Web Token для добавления.
    :param exp: Срок действия токена.
    :raises ExternalServiceError: При ошибке взаимодействия с Redis.
    """

    try:
        async for redis in get_redis_service():
            token_hash = generate_hash_token(jwt)
            keys = await _scan_keys(redis, f"refresh_token:{uid}:*")
            if len(keys) >= 4:
                # delete the oldest by timestamp in key suffix
                oldest_key = min(keys, key=lambda k: int(k.rsplit(":", 1)[-1]))
                await redis.delete(oldest_key)
            timestamp = time.time_ns()
            await redis.set(
                f"refresh_token:{uid}:{token_hash}:{timestamp}",
                "valid",
                ex=exp,
            )
            # log.info("Refresh token added to redis")
    except RedisError as e:
        log.error(
            "Redis error adding refresh token: %s",
            e,
        )
        raise ExternalServiceError(
            "Ошибка авторизации. Пожалуйста, войдите заново",
            service_name="Redis",
            original_error=e,
        )


async def validate_refresh_jwt(
    uid: str,
    refresh_token: str,
    redis: Redis,
) -> bool:
    """
    Проверяет refresh токен для указанного пользователя.

    Проверяет refresh токен из базы данных Redis для указанного ID пользователя
    и refresh токена. Токен хешируется и соответствующие ключи в Redis
    проверяются на существование. Если токен недействителен, истек или не существует,
    возвращает False.

    :param uid: ID пользователя для проверки refresh токена.
    :param refresh_token: Refresh токен для проверки.
    :param redis: Клиент Redis для выполнения запроса.
    :return: True, если токен действителен, иначе False.
    :raises ExternalServiceError: При ошибке взаимодействия с Redis.
    """

    try:
        token_hash = generate_hash_token(refresh_token)
        # Fast existence check via SCAN
        async for _ in redis.scan_iter(
            match=f"refresh_token:{uid}:{token_hash}:*", count=100
        ):
            return True
        return False
    except RedisError as e:
        log.error(
            "Redis error validating refresh token: %s",
            str(e),
        )
        raise ExternalServiceError(
            "Ошибка аутентификации. Пожалуйста, войдите заново",
            service_name="Redis",
            original_error=e,
        )


async def revoke_refresh_token(
    uid: str,
    refresh_token: str,
    redis: Redis,
) -> None:
    """
    Отзывает refresh токен для указанного пользователя.

    Отзывает refresh токен из базы данных Redis для указанного ID пользователя
    и refresh токена. Токен хешируется и соответствующий ключ в Redis
    удаляется. Функция логирует сообщение при успешном отзыве токена.

    :param uid: ID пользователя для отзыва refresh токена.
    :param refresh_token: Refresh токен для отзыва.
    :param redis: Клиент Redis для выполнения запроса.
    :return: None.
    :raises ExternalServiceError: При ошибке взаимодействия с Redis.
    """

    token_hash = generate_hash_token(refresh_token)
    try:
        keys_to_delete = [
            k
            async for k in redis.scan_iter(
                match=f"refresh_token:{uid}:{token_hash}:*", count=100
            )
        ]
        if keys_to_delete:
            await redis.delete(*keys_to_delete)
            # log.info("Refresh token revoked")
    except RedisError as e:
        log.error(
            "Redis error revoking refresh token: %s",
            str(e),
        )
        raise ExternalServiceError(
            "Ошибка сервера",
            service_name="Redis",
            original_error=e,
        )


async def revoke_all_refresh_tokens(
    uid: str,
) -> None:
    """
    Отзывает все refresh токены для указанного пользователя.

    Эта функция отзывает все refresh токены для указанного ID пользователя,
    удаляя соответствующие ключи из Redis. Если возникают ошибки Redis
    в процессе, вызывается HTTPException со статусом 401.

    :param uid: ID пользователя для отзыва всех refresh токенов.
    :type uid: str
    :raises ExternalServiceError: При ошибке взаимодействия с Redis.
    """

    try:
        async for redis in get_redis_service():
            keys = [
                k
                async for k in redis.scan_iter(
                    match=f"refresh_token:{uid}:*", count=200
                )
            ]
            if keys:
                await redis.delete(*keys)
                # log.info("All refresh tokens revoked")
    except RedisError as e:
        log.error(
            "Redis error revoking refresh tokens: %s",
            str(e),
        )
        raise ExternalServiceError(
            "Ошибка сервера",
            service_name="Redis",
            original_error=e,
        )


def get_redis_session_from_request(request: Request) -> Redis:
    """
    Получает сессию Redis, связанную с указанным запросом.

    :param request: Объект запроса.
    :type request: Request
    :return: Сессия Redis, связанная с запросом, или пустой словарь.
    :rtype: Redis
    """

    return request.scope.get("redis_session", {})
