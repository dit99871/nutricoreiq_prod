"""
Тесты для утилит работы с пользователем.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.core.schemas.user import UserPublic
from src.app.core.utils import user


@pytest.fixture
def mock_request():
    """Создает мок для Request."""
    request = MagicMock(spec=Request)
    request.cookies = {}
    return request


@pytest.fixture
def mock_session():
    """Создает мок для AsyncSession."""
    session = AsyncMock(spec=AsyncSession)
    return session


@pytest.fixture
def user_public():
    """Валидные данные публичного пользователя."""
    return UserPublic(
        id=1,
        uid="test-uid-123",
        username="testuser",
        email="test@example.com",
    )


# --- get_user_from_request ---


@pytest.mark.asyncio
@patch("src.app.core.services.jwt_service.get_jwt_from_cookies")
async def test_get_user_from_request_no_token(mock_get_jwt_from_cookies, mock_request, mock_session):
    """Тест случая когда токен отсутствует в cookies."""
    from src.app.core.utils.user import get_user_from_request

    mock_get_jwt_from_cookies.return_value = None

    result = await get_user_from_request(mock_request, mock_session)

    assert result is None
    mock_get_jwt_from_cookies.assert_called_once_with(mock_request)


@pytest.mark.asyncio
@patch("src.app.core.services.jwt_service.get_jwt_payload")
@patch("src.app.core.services.jwt_service.get_jwt_from_cookies")
async def test_get_user_from_request_invalid_token_type(
    mock_get_jwt_from_cookies, mock_get_jwt_payload, mock_request, mock_session
):
    """Тест случая когда токен имеет неверный тип."""
    from src.app.core.utils.user import get_user_from_request
    from src.app.core.constants import ACCESS_TOKEN_TYPE, TOKEN_TYPE_FIELD

    mock_get_jwt_from_cookies.return_value = "valid_token"
    mock_get_jwt_payload.return_value = {TOKEN_TYPE_FIELD: "refresh"}

    result = await get_user_from_request(mock_request, mock_session)

    assert result is None


@pytest.mark.asyncio
@patch("src.app.core.services.jwt_service.get_jwt_payload")
@patch("src.app.core.services.jwt_service.get_jwt_from_cookies")
async def test_get_user_from_request_no_sub_in_payload(
    mock_get_jwt_from_cookies, mock_get_jwt_payload, mock_request, mock_session
):
    """Тест случая когда в payload отсутствует sub."""
    from src.app.core.utils.user import get_user_from_request
    from src.app.core.constants import ACCESS_TOKEN_TYPE, TOKEN_TYPE_FIELD

    mock_get_jwt_from_cookies.return_value = "valid_token"
    mock_get_jwt_payload.return_value = {TOKEN_TYPE_FIELD: ACCESS_TOKEN_TYPE}

    result = await get_user_from_request(mock_request, mock_session)

    assert result is None


@pytest.mark.asyncio
@patch("src.app.core.repo.user.get_user_by_uid")
@patch("src.app.core.services.jwt_service.get_jwt_payload")
@patch("src.app.core.services.jwt_service.get_jwt_from_cookies")
async def test_get_user_from_request_user_not_found(
    mock_get_jwt_from_cookies, mock_get_jwt_payload, mock_get_user_by_uid, mock_request, mock_session
):
    """Тест случая когда пользователь не найден в БД."""
    from src.app.core.utils.user import get_user_from_request
    from src.app.core.constants import ACCESS_TOKEN_TYPE, TOKEN_TYPE_FIELD

    mock_get_jwt_from_cookies.return_value = "valid_token"
    mock_get_jwt_payload.return_value = {TOKEN_TYPE_FIELD: ACCESS_TOKEN_TYPE, "sub": "test-uid"}
    mock_get_user_by_uid.return_value = None

    result = await get_user_from_request(mock_request, mock_session)

    assert result is None
    mock_get_user_by_uid.assert_called_once_with(mock_session, "test-uid")


@pytest.mark.asyncio
@patch("src.app.core.repo.user.get_user_by_uid")
@patch("src.app.core.services.jwt_service.get_jwt_payload")
@patch("src.app.core.services.jwt_service.get_jwt_from_cookies")
async def test_get_user_from_request_success(
    mock_get_jwt_from_cookies, mock_get_jwt_payload, mock_get_user_by_uid, mock_request, mock_session, user_public
):
    """Тест успешного получения пользователя."""
    from src.app.core.utils.user import get_user_from_request
    from src.app.core.constants import ACCESS_TOKEN_TYPE, TOKEN_TYPE_FIELD

    mock_get_jwt_from_cookies.return_value = "valid_token"
    mock_get_jwt_payload.return_value = {TOKEN_TYPE_FIELD: ACCESS_TOKEN_TYPE, "sub": "test-uid-123"}
    mock_get_user_by_uid.return_value = user_public

    result = await get_user_from_request(mock_request, mock_session)

    assert result == user_public
    mock_get_user_by_uid.assert_called_once_with(mock_session, "test-uid-123")


@pytest.mark.asyncio
@patch("src.app.core.services.jwt_service.get_jwt_from_cookies")
async def test_get_user_from_request_exception_handling(mock_get_jwt_from_cookies, mock_request, mock_session):
    """Тест обработки исключений."""
    from src.app.core.utils.user import get_user_from_request

    mock_get_jwt_from_cookies.side_effect = Exception("JWT error")

    result = await get_user_from_request(mock_request, mock_session)

    assert result is None


@pytest.mark.asyncio
@patch("src.app.core.services.jwt_service.get_jwt_payload")
@patch("src.app.core.services.jwt_service.get_jwt_from_cookies")
async def test_get_user_from_request_payload_exception(
    mock_get_jwt_from_cookies, mock_get_jwt_payload, mock_request, mock_session
):
    """Тест обработки исключения при декодировании payload."""
    from src.app.core.utils.user import get_user_from_request

    mock_get_jwt_from_cookies.return_value = "valid_token"
    mock_get_jwt_payload.side_effect = Exception("Decode error")

    result = await get_user_from_request(mock_request, mock_session)

    assert result is None


@pytest.mark.asyncio
@patch("src.app.core.repo.user.get_user_by_uid")
@patch("src.app.core.services.jwt_service.get_jwt_payload")
@patch("src.app.core.services.jwt_service.get_jwt_from_cookies")
async def test_get_user_from_request_db_exception(
    mock_get_jwt_from_cookies, mock_get_jwt_payload, mock_get_user_by_uid, mock_request, mock_session
):
    """Тест обработки исключения при запросе к БД."""
    from src.app.core.utils.user import get_user_from_request
    from src.app.core.constants import ACCESS_TOKEN_TYPE, TOKEN_TYPE_FIELD

    mock_get_jwt_from_cookies.return_value = "valid_token"
    mock_get_jwt_payload.return_value = {TOKEN_TYPE_FIELD: ACCESS_TOKEN_TYPE, "sub": "test-uid"}
    mock_get_user_by_uid.side_effect = Exception("DB error")

    result = await get_user_from_request(mock_request, mock_session)

    assert result is None


# --- optional_current_user ---


def test_optional_current_user_returns_dependency():
    """Тест что optional_current_user возвращает функцию-зависимость."""
    from src.app.core.utils.user import optional_current_user

    dependency = optional_current_user()

    assert callable(dependency)


@pytest.mark.asyncio
@patch("src.app.core.utils.user.get_user_from_request")
async def test_optional_current_user_dependency_calls_get_user_from_request(
    mock_get_user_from_request, mock_request, mock_session, user_public
):
    """Тест что dependency вызывает get_user_from_request."""
    from src.app.core.utils.user import optional_current_user

    mock_get_user_from_request.return_value = user_public
    dependency = optional_current_user()

    result = await dependency(mock_request, mock_session)

    assert result == user_public
    mock_get_user_from_request.assert_called_once_with(mock_request, mock_session)


@pytest.mark.asyncio
@patch("src.app.core.utils.user.get_user_from_request")
async def test_optional_current_user_dependency_returns_none_on_no_user(
    mock_get_user_from_request, mock_request, mock_session
):
    """Тест что dependency возвращает None когда пользователь не найден."""
    from src.app.core.utils.user import optional_current_user

    mock_get_user_from_request.return_value = None
    dependency = optional_current_user()

    result = await dependency(mock_request, mock_session)

    assert result is None


