import pytest
from unittest.mock import AsyncMock, patch
from fastapi import HTTPException, status
from redis.asyncio import Redis, RedisError

from src.app.services.redis import (
    add_refresh_to_redis,
    validate_refresh_jwt,
    revoke_refresh_token,
    revoke_all_refresh_tokens,
)


# Фикстура для мок-объекта Redis
@pytest.fixture
def mock_redis():
    redis = AsyncMock(spec=Redis)
    redis.keys = AsyncMock()
    redis.set = AsyncMock()
    redis.delete = AsyncMock()
    redis.exists = AsyncMock()
    return redis


# Фикстура для мок-генератора get_redis
@pytest.fixture
def mock_get_redis(mock_redis):
    async def mock_redis_gen():
        yield mock_redis

    with patch("src.app.services.redis.get_redis", mock_redis_gen):
        yield mock_redis


# Тесты для add_refresh_to_redis
@pytest.mark.asyncio
async def test_add_refresh_to_redis_success(mock_get_redis):
    """Проверяет успешное добавление refresh токена."""
    mock_redis = mock_get_redis
    mock_redis.keys.return_value = []
    with patch(
        "src.app.services.redis.generate_hash_token", return_value="hashed_token"
    ):
        await add_refresh_to_redis("user1", "jwt_token", 3600)
    mock_redis.set.assert_called()


@pytest.mark.asyncio
async def test_add_refresh_to_redis_limit_exceeded(mock_get_redis):
    """Проверяет удаление старого токена при превышении лимита (4)."""
    mock_redis = mock_get_redis
    mock_redis.keys.return_value = [f"refresh_token:user1:token1:{i}" for i in range(4)]
    with patch("src.app.services.redis.generate_hash_token", return_value="new_token"):
        await add_refresh_to_redis("user1", "new_jwt", 3600)
    assert mock_redis.delete.call_count == 1
    assert mock_redis.set.call_count == 1


@pytest.mark.asyncio
async def test_add_refresh_to_redis_redis_error(mock_get_redis):
    """Проверяет обработку ошибки Redis."""
    mock_redis = mock_get_redis
    mock_redis.keys.side_effect = RedisError("Redis error")
    with pytest.raises(HTTPException) as exc:
        await add_refresh_to_redis("user1", "jwt_token", 3600)
    assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert "Redis error adding refresh token" in exc.value.detail


# Тесты для validate_refresh_jwt
@pytest.mark.asyncio
async def test_validate_refresh_jwt_success(mock_redis):
    """Проверяет успешную валидацию токена."""
    mock_redis.keys.return_value = ["refresh_token:user1:hashed_token:123"]
    with patch(
        "src.app.services.redis.generate_hash_token", return_value="hashed_token"
    ):
        result = await validate_refresh_jwt("user1", "refresh_token", mock_redis)
    assert result is True
    mock_redis.keys.assert_called()


@pytest.mark.asyncio
async def test_validate_refresh_jwt_failure(mock_redis):
    """Проверяет провал валидации токена."""
    mock_redis.keys.return_value = []
    with patch(
        "src.app.services.redis.generate_hash_token", return_value="hashed_token"
    ):
        result = await validate_refresh_jwt("user1", "refresh_token", mock_redis)
    assert result is False
    mock_redis.keys.assert_called()


# Тесты для revoke_refresh_token
@pytest.mark.asyncio
async def test_revoke_refresh_token_success(mock_redis):
    """Проверяет успешную отозву токена."""
    mock_redis.keys.return_value = ["refresh_token:user1:hashed_token:123"]
    with patch(
        "src.app.services.redis.generate_hash_token", return_value="hashed_token"
    ) as mock_generate_hash:
        await revoke_refresh_token("user1", "refresh_token", mock_redis)
        print(f"mock_redis.keys call args: {mock_redis.keys.call_args}")
        print(f"mock_generate_hash call args: {mock_generate_hash.call_args}")
    mock_redis.keys.assert_called_with("refresh_token:user1:hashed_token:*")
    mock_redis.delete.assert_called_with("refresh_token:user1:hashed_token:123")


# Тесты для revoke_all_refresh_tokens
@pytest.mark.asyncio
async def test_revoke_all_refresh_tokens_success(mock_get_redis):
    """Проверяет успешную отозву всех токенов."""
    mock_redis = mock_get_redis
    mock_redis.keys.return_value = [
        "refresh_token:user1:token1",
        "refresh_token:user1:token2",
    ]
    await revoke_all_refresh_tokens("user1")
    mock_redis.delete.assert_called_with(
        "refresh_token:user1:token1", "refresh_token:user1:token2"
    )


@pytest.mark.asyncio
async def test_revoke_all_refresh_tokens_redis_error(mock_get_redis):
    """Проверяет обработку ошибки Redis."""
    mock_redis = mock_get_redis
    mock_redis.keys.side_effect = RedisError("Redis error")
    with pytest.raises(HTTPException) as exc:
        await revoke_all_refresh_tokens("user1")
    assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert "Redis error revoking refresh tokens" in exc.value.detail
