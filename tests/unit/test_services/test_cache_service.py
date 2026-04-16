"""
Тесты для CacheService.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.app.core.services.cache import CacheService


class TestCacheService:
    """Тесты для CacheService."""

    def test_get_user_cache_key(self):
        """Проверяем генерацию ключа кеша для пользователя."""
        uid = "user123"
        expected_key = f"user:{uid}"
        actual_key = CacheService._get_user_cache_key(uid)
        assert actual_key == expected_key

    def test_get_user_cache_key_different_uids(self):
        """Проверяем, что разные UID дают разные ключи."""
        uid1 = "user123"
        uid2 = "user456"
        key1 = CacheService._get_user_cache_key(uid1)
        key2 = CacheService._get_user_cache_key(uid2)
        assert key1 != key2
        assert key1 == "user:user123"
        assert key2 == "user:user456"

    @pytest.mark.asyncio
    async def test_get_user_success(self):
        """Проверяем успешное получение данных пользователя из кеша."""
        uid = "user123"
        user_data = {"id": uid, "email": "test@example.com", "name": "Test User"}
        cached_data = json.dumps(user_data)

        mock_redis = AsyncMock()
        mock_redis.get.return_value = cached_data

        with patch("src.app.core.services.cache.get_redis_service") as mock_get_redis:
            mock_get_redis.return_value.__aiter__.return_value = [mock_redis]
            
            result = await CacheService.get_user(uid)
            
            assert result == user_data
            mock_redis.get.assert_called_once_with("user:user123")

    @pytest.mark.asyncio
    async def test_get_user_not_found(self):
        """Проверяем случай, когда пользователь не найден в кеше."""
        uid = "nonexistent"
        mock_redis = AsyncMock()
        mock_redis.get.return_value = None

        with patch("src.app.core.services.cache.get_redis_service") as mock_get_redis:
            mock_get_redis.return_value.__aiter__.return_value = [mock_redis]
            
            result = await CacheService.get_user(uid)
            
            assert result is None
            mock_redis.get.assert_called_once_with("user:nonexistent")

    @pytest.mark.asyncio
    async def test_get_user_json_decode_error(self):
        """Проверяем обработку ошибки JSON декодирования."""
        uid = "user123"
        invalid_json = "{invalid json data"
        mock_redis = AsyncMock()
        mock_redis.get.return_value = invalid_json

        with patch("src.app.core.services.cache.get_redis_service") as mock_get_redis:
            with patch("src.app.core.services.cache.log") as mock_log:
                mock_get_redis.return_value.__aiter__.return_value = [mock_redis]
                
                result = await CacheService.get_user(uid)
                
                assert result is None
                mock_log.error.assert_called_once()
                # Проверяем, что ошибка содержит UID и информацию об ошибке
                error_call_args = mock_log.error.call_args[0]
                assert uid in str(error_call_args)
                assert "Ошибка десериализации" in str(error_call_args)

    @pytest.mark.asyncio
    async def test_get_user_redis_exception(self):
        """Проверяем обработку исключения Redis."""
        uid = "user123"
        mock_redis = AsyncMock()
        mock_redis.get.side_effect = Exception("Redis connection error")

        with patch("src.app.core.services.cache.get_redis_service") as mock_get_redis:
            with patch("src.app.core.services.cache.log") as mock_log:
                mock_get_redis.return_value.__aiter__.return_value = [mock_redis]
                
                result = await CacheService.get_user(uid)
                
                assert result is None
                mock_log.error.assert_called_once()
                # Проверяем, что ошибка содержит информацию об ошибке
                error_call_args = mock_log.error.call_args[0]
                assert "Ошибка при получении пользователя из кеша" in str(error_call_args)

    @pytest.mark.asyncio
    async def test_get_user_debug_logging(self):
        """Проверяем логирование при успешном получении данных."""
        uid = "user123"
        user_data = {"id": uid, "email": "test@example.com"}
        cached_data = json.dumps(user_data)
        mock_redis = AsyncMock()
        mock_redis.get.return_value = cached_data

        with patch("src.app.core.services.cache.get_redis_service") as mock_get_redis:
            with patch("src.app.core.services.cache.log") as mock_log:
                mock_get_redis.return_value.__aiter__.return_value = [mock_redis]
                
                result = await CacheService.get_user(uid)
                
                assert result == user_data
                mock_log.debug.assert_called_once_with("Данные пользователя %s получены из кеша", uid)

    @pytest.mark.asyncio
    async def test_get_user_empty_string(self):
        """Проверяем обработку пустой строки в кеше."""
        uid = "user123"
        mock_redis = AsyncMock()
        mock_redis.get.return_value = ""

        with patch("src.app.core.services.cache.get_redis_service") as mock_get_redis:
            mock_get_redis.return_value.__aiter__.return_value = [mock_redis]
            
            result = await CacheService.get_user(uid)
            
            assert result is None
            mock_redis.get.assert_called_once_with("user:user123")

    @pytest.mark.asyncio
    async def test_get_user_whitespace_string(self):
        """Проверяем обработку строки с пробелами."""
        uid = "user123"
        whitespace_data = "   "
        mock_redis = AsyncMock()
        mock_redis.get.return_value = whitespace_data

        with patch("src.app.core.services.cache.get_redis_service") as mock_get_redis:
            mock_get_redis.return_value.__aiter__.return_value = [mock_redis]
            
            result = await CacheService.get_user(uid)
            
            assert result is None

    @pytest.mark.asyncio
    async def test_get_user_valid_json_string(self):
        """Проверяем обработку валидной JSON строки."""
        uid = "user123"
        user_data = {"id": uid, "email": "test@example.com", "active": True}
        cached_data = json.dumps(user_data)
        mock_redis = AsyncMock()
        mock_redis.get.return_value = cached_data

        with patch("src.app.core.services.cache.get_redis_service") as mock_get_redis:
            mock_get_redis.return_value.__aiter__.return_value = [mock_redis]
            
            result = await CacheService.get_user(uid)
            
            assert result == user_data
            assert result["id"] == uid
            assert result["email"] == "test@example.com"
            assert result["active"] is True

    @pytest.mark.asyncio
    async def test_get_user_complex_json_structure(self):
        """Проверяем обработку сложной JSON структуры."""
        uid = "user123"
        user_data = {
            "id": uid,
            "profile": {
                "name": "Test User",
                "preferences": {
                    "theme": "dark",
                    "notifications": True
                }
            },
            "roles": ["user", "admin"],
            "metadata": None
        }
        cached_data = json.dumps(user_data)
        mock_redis = AsyncMock()
        mock_redis.get.return_value = cached_data

        with patch("src.app.core.services.cache.get_redis_service") as mock_get_redis:
            mock_get_redis.return_value.__aiter__.return_value = [mock_redis]
            
            result = await CacheService.get_user(uid)
            
            assert result == user_data
            assert result["profile"]["preferences"]["theme"] == "dark"
            assert "admin" in result["roles"]
            assert result["metadata"] is None

    def test_get_user_cache_key_is_static_method(self):
        """Проверяем, что _get_user_cache_key является статическим методом."""
        assert hasattr(CacheService._get_user_cache_key, '__self__') is False

    def test_get_user_is_classmethod(self):
        """Проверяем, что get_user является класс методом."""
        import inspect
        assert inspect.ismethod(CacheService.get_user) is True
        # Проверяем, что метод можно вызывать на классе без инстанса
        assert callable(CacheService.get_user)
