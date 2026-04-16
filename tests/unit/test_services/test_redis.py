"""
Тесты для Redis сервиса.
"""

import datetime as dt
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import Request
from redis.asyncio import Redis, RedisError

from src.app.core.exceptions import ExternalServiceError
from src.app.core.services.redis import (
    _scan_keys,
    add_refresh_jwt_to_redis,
    get_redis_session_from_request,
    revoke_all_refresh_tokens,
    revoke_refresh_token,
    validate_refresh_jwt,
)


@pytest.fixture
def mock_redis():
    """Создает мок для Redis."""
    redis = AsyncMock(spec=Redis)
    return redis


@pytest.fixture
def mock_request():
    """Создает мок для Request."""
    request = MagicMock(spec=Request)
    request.scope = {}
    return request


# --- _scan_keys ---


@pytest.mark.asyncio
async def test_scan_keys_empty(mock_redis):
    """Тест сканирования ключей без результатов."""
    async def async_scan_iter():
        return
        yield  # pragma: no cover
    mock_redis.scan_iter.return_value = async_scan_iter()

    keys = await _scan_keys(mock_redis, "pattern:*")

    assert keys == []
    mock_redis.scan_iter.assert_called_once_with(match="pattern:*", count=100)


@pytest.mark.asyncio
async def test_scan_keys_with_results(mock_redis):
    """Тест сканирования ключей с результатами."""
    async def async_scan_iter():
        yield "key1"
        yield "key2"
        yield "key3"
    mock_redis.scan_iter.return_value = async_scan_iter()

    keys = await _scan_keys(mock_redis, "pattern:*")

    assert keys == ["key1", "key2", "key3"]
    mock_redis.scan_iter.assert_called_once_with(match="pattern:*", count=100)


@pytest.mark.asyncio
async def test_scan_keys_custom_count(mock_redis):
    """Тест сканирования ключей с кастомным count."""
    async def async_scan_iter():
        yield "key1"
    mock_redis.scan_iter.return_value = async_scan_iter()

    keys = await _scan_keys(mock_redis, "pattern:*", count=50)

    assert keys == ["key1"]
    mock_redis.scan_iter.assert_called_once_with(match="pattern:*", count=50)


# --- add_refresh_jwt_to_redis ---


@pytest.mark.asyncio
@patch("src.app.core.services.redis.get_redis_service")
@patch("src.app.core.services.redis.generate_hash_token")
@patch("src.app.core.services.redis._scan_keys")
async def test_add_refresh_jwt_to_redis_success(mock_scan_keys, mock_generate_hash, mock_get_redis):
    """Тест успешного добавления refresh токена."""
    mock_redis = AsyncMock(spec=Redis)
    mock_redis.set = AsyncMock()
    mock_redis.delete = AsyncMock()
    
    async def redis_gen():
        yield mock_redis
    mock_get_redis.return_value = redis_gen()
    mock_generate_hash.return_value = "hashed_token"
    mock_scan_keys.return_value = []

    exp = dt.timedelta(hours=1)

    await add_refresh_jwt_to_redis("user123", "jwt_token", exp)

    mock_redis.set.assert_called_once()
    call_args = mock_redis.set.call_args
    assert "refresh_token:user123:hashed_token:" in call_args[0][0]


@pytest.mark.asyncio
@patch("src.app.core.services.redis.get_redis_service")
@patch("src.app.core.services.redis.generate_hash_token")
@patch("src.app.core.services.redis._scan_keys")
async def test_add_refresh_jwt_to_redis_delete_oldest(mock_scan_keys, mock_generate_hash, mock_get_redis):
    """Тест удаления старейшего токена при достижении лимита."""
    mock_redis = AsyncMock(spec=Redis)
    mock_redis.set = AsyncMock()
    mock_redis.delete = AsyncMock()
    
    async def redis_gen():
        yield mock_redis
    mock_get_redis.return_value = redis_gen()
    mock_generate_hash.return_value = "hashed_token"
    mock_scan_keys.return_value = [
        "refresh_token:user123:hash1:1000000000",
        "refresh_token:user123:hash2:2000000000",
        "refresh_token:user123:hash3:3000000000",
        "refresh_token:user123:hash4:4000000000",
    ]

    exp = dt.timedelta(hours=1)

    await add_refresh_jwt_to_redis("user123", "jwt_token", exp)

    mock_redis.delete.assert_called_once_with("refresh_token:user123:hash1:1000000000")
    mock_redis.set.assert_called_once()


@pytest.mark.asyncio
@patch("src.app.core.services.redis.get_redis_service")
async def test_add_refresh_jwt_to_redis_redis_error(mock_get_redis):
    """Тест обработки ошибки Redis при добавлении токена."""
    async def redis_gen():
        mock_redis = AsyncMock(spec=Redis)
        class AsyncIterator:
            def __aiter__(self):
                return self
            async def __anext__(self):
                raise RedisError("Redis error")
        mock_redis.scan_iter.return_value = AsyncIterator()
        yield mock_redis
    mock_get_redis.return_value = redis_gen()

    exp = dt.timedelta(hours=1)

    with pytest.raises(ExternalServiceError) as exc_info:
        await add_refresh_jwt_to_redis("user123", "jwt_token", exp)

    assert "авторизации" in str(exc_info.value)


# --- validate_refresh_jwt ---


@pytest.mark.asyncio
@patch("src.app.core.services.redis.generate_hash_token")
async def test_validate_refresh_jwt_valid(mock_generate_hash, mock_redis):
    """Тест валидации валидного refresh токена."""
    mock_generate_hash.return_value = "hashed_token"
    async def scan_gen():
        yield "refresh_token:user123:hashed_token:timestamp"
    mock_redis.scan_iter.return_value = scan_gen()

    result = await validate_refresh_jwt("user123", "jwt_token", mock_redis)

    assert result is True
    mock_redis.scan_iter.assert_called_once()


@pytest.mark.asyncio
@patch("src.app.core.services.redis.generate_hash_token")
async def test_validate_refresh_jwt_invalid(mock_generate_hash, mock_redis):
    """Тест валидации невалидного refresh токена."""
    mock_generate_hash.return_value = "hashed_token"
    async def scan_gen():
        return
        yield  # pragma: no cover
    mock_redis.scan_iter.return_value = scan_gen()

    result = await validate_refresh_jwt("user123", "jwt_token", mock_redis)

    assert result is False


@pytest.mark.asyncio
@patch("src.app.core.services.redis.generate_hash_token")
async def test_validate_refresh_jwt_redis_error(mock_generate_hash, mock_redis):
    """Тест обработки ошибки Redis при валидации токена."""
    mock_generate_hash.return_value = "hashed_token"
    class AsyncIterator:
        def __aiter__(self):
            return self
        async def __anext__(self):
            raise RedisError("Redis error")
    mock_redis.scan_iter.return_value = AsyncIterator()

    with pytest.raises(ExternalServiceError) as exc_info:
        await validate_refresh_jwt("user123", "jwt_token", mock_redis)

    assert "аутентификации" in str(exc_info.value)


# --- revoke_refresh_token ---


@pytest.mark.asyncio
@patch("src.app.core.services.redis.generate_hash_token")
async def test_revoke_refresh_token_success(mock_generate_hash, mock_redis):
    """Тест успешного отзыва refresh токена."""
    mock_generate_hash.return_value = "hashed_token"
    async def scan_gen():
        yield "refresh_token:user123:hashed_token:timestamp"
    mock_redis.scan_iter.return_value = scan_gen()
    mock_redis.delete = AsyncMock()

    await revoke_refresh_token("user123", "jwt_token", mock_redis)

    mock_redis.delete.assert_called_once_with("refresh_token:user123:hashed_token:timestamp")


@pytest.mark.asyncio
@patch("src.app.core.services.redis.generate_hash_token")
async def test_revoke_refresh_token_no_keys(mock_generate_hash, mock_redis):
    """Тест отзыва несуществующего токена."""
    mock_generate_hash.return_value = "hashed_token"
    async def scan_gen():
        return
        yield  # pragma: no cover
    mock_redis.scan_iter.return_value = scan_gen()

    await revoke_refresh_token("user123", "jwt_token", mock_redis)

    mock_redis.delete.assert_not_called()


@pytest.mark.asyncio
@patch("src.app.core.services.redis.generate_hash_token")
async def test_revoke_refresh_token_multiple_keys(mock_generate_hash, mock_redis):
    """Тест отзыва токена с несколькими ключами."""
    mock_generate_hash.return_value = "hashed_token"
    async def scan_gen():
        yield "refresh_token:user123:hashed_token:timestamp1"
        yield "refresh_token:user123:hashed_token:timestamp2"
    mock_redis.scan_iter.return_value = scan_gen()
    mock_redis.delete = AsyncMock()

    await revoke_refresh_token("user123", "jwt_token", mock_redis)

    mock_redis.delete.assert_called_once()
    call_args = mock_redis.delete.call_args[0]
    assert len(call_args) == 2


@pytest.mark.asyncio
@patch("src.app.core.services.redis.generate_hash_token")
async def test_revoke_refresh_token_redis_error(mock_generate_hash, mock_redis):
    """Тест обработки ошибки Redis при отзыве токена."""
    mock_generate_hash.return_value = "hashed_token"
    class AsyncIterator:
        def __aiter__(self):
            return self
        async def __anext__(self):
            raise RedisError("Redis error")
    mock_redis.scan_iter.return_value = AsyncIterator()

    with pytest.raises(ExternalServiceError) as exc_info:
        await revoke_refresh_token("user123", "jwt_token", mock_redis)

    assert "сервер" in str(exc_info.value)


# --- revoke_all_refresh_tokens ---


@pytest.mark.asyncio
@patch("src.app.core.services.redis.get_redis_service")
async def test_revoke_all_refresh_tokens_success(mock_get_redis):
    """Тест успешного отзыва всех refresh токенов."""
    mock_redis = AsyncMock(spec=Redis)
    mock_redis.delete = AsyncMock()
    
    async def redis_gen():
        async def scan_gen():
            yield "refresh_token:user123:hash1:timestamp1"
            yield "refresh_token:user123:hash2:timestamp2"
        mock_redis.scan_iter.return_value = scan_gen()
        yield mock_redis
    mock_get_redis.return_value = redis_gen()

    await revoke_all_refresh_tokens("user123")

    mock_redis.delete.assert_called_once()
    call_args = mock_redis.delete.call_args[0]
    assert len(call_args) == 2


@pytest.mark.asyncio
@patch("src.app.core.services.redis.get_redis_service")
async def test_revoke_all_refresh_tokens_no_tokens(mock_get_redis):
    """Тест отзыва всех токенов когда токенов нет."""
    async def redis_gen():
        mock_redis = AsyncMock(spec=Redis)
        mock_redis.delete = AsyncMock()
        async def scan_gen():
            return
            yield  # pragma: no cover
        mock_redis.scan_iter.return_value = scan_gen()
        yield mock_redis
    mock_get_redis.return_value = redis_gen()

    await revoke_all_refresh_tokens("user123")

    async_gen = redis_gen()
    mock_redis = await async_gen.__anext__()
    mock_redis.delete.assert_not_called()


@pytest.mark.asyncio
@patch("src.app.core.services.redis.get_redis_service")
async def test_revoke_all_refresh_tokens_redis_error(mock_get_redis):
    """Тест обработки ошибки Redis при отзыве всех токенов."""
    async def redis_gen():
        mock_redis = AsyncMock(spec=Redis)
        class AsyncIterator:
            def __aiter__(self):
                return self
            async def __anext__(self):
                raise RedisError("Redis error")
        mock_redis.scan_iter.return_value = AsyncIterator()
        yield mock_redis
    mock_get_redis.return_value = redis_gen()

    with pytest.raises(ExternalServiceError) as exc_info:
        await revoke_all_refresh_tokens("user123")

    assert "сервер" in str(exc_info.value)


# --- get_redis_session_from_request ---


def test_get_redis_session_from_request_exists(mock_request):
    """Тест получения Redis сессии когда она существует."""
    mock_redis = AsyncMock(spec=Redis)
    mock_request.scope = {"redis_session": mock_redis}

    result = get_redis_session_from_request(mock_request)

    assert result == mock_redis


def test_get_redis_session_from_request_not_exists(mock_request):
    """Тест получения Redis сессии когда она не существует."""
    mock_request.scope = {}

    result = get_redis_session_from_request(mock_request)

    assert result == {}
