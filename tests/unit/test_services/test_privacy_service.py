"""
Тесты для PrivacyService.
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.core.models.privacy_consent import ConsentType
from src.app.core.schemas.privacy import PrivacyConsentRequest
from src.app.core.schemas.user import UserPublic
from src.app.core.services.privacy_service import PrivacyService, get_privacy_service


@pytest.fixture
def mock_request():
    """Создает мок для Request."""
    request = MagicMock(spec=Request)
    request.scope = {"redis_session": {"redis_session_id": "test-session-id"}}
    request.state = MagicMock()
    request.state.client_ip = "192.168.1.1"
    request.headers = {"user-agent": "Mozilla/5.0"}
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


@pytest.fixture
def consent_data():
    """Валидные данные согласия."""
    return PrivacyConsentRequest(
        personal_data=True,
        cookies=True,
        marketing=False,
    )


# --- save_consent ---


@pytest.mark.asyncio
@patch("src.app.core.services.privacy_service.create_privacy_consent")
@patch("src.app.core.services.privacy_service.ConsentCacheService")
async def test_save_consent_authorized_user(
    mock_cache_service, mock_create_privacy_consent, mock_request, mock_session, user_public, consent_data
):
    """Тест сохранения согласия для авторизованного пользователя."""
    mock_create_privacy_consent.return_value = None
    mock_cache_service.invalidate = AsyncMock()

    await PrivacyService.save_consent(mock_request, mock_session, user_public, consent_data)

    assert mock_create_privacy_consent.call_count == 2  # personal_data и cookies
    assert mock_cache_service.invalidate.call_count == 2  # invalidate вызывается для каждого типа согласия
    mock_cache_service.invalidate.assert_called_with(1)


@pytest.mark.asyncio
@patch("src.app.core.services.privacy_service.create_privacy_consent")
@patch("src.app.core.services.privacy_service.ConsentCacheService")
async def test_save_consent_unauthorized_user(
    mock_cache_service, mock_create_privacy_consent, mock_request, mock_session, consent_data
):
    """Тест сохранения согласия для неавторизованного пользователя."""
    mock_create_privacy_consent.return_value = None

    await PrivacyService.save_consent(mock_request, mock_session, None, consent_data)

    assert mock_create_privacy_consent.call_count == 2
    # Проверяем что session_id передается, а user_id = None
    first_call = mock_create_privacy_consent.call_args_list[0]
    assert first_call[1]["session_id"] == "test-session-id"
    assert first_call[1]["user_id"] is None
    mock_cache_service.invalidate.assert_not_called()


@pytest.mark.asyncio
@patch("src.app.core.services.privacy_service.create_privacy_consent")
@patch("src.app.core.services.privacy_service.ConsentCacheService")
async def test_save_consent_all_consent_types(
    mock_cache_service, mock_create_privacy_consent, mock_request, mock_session, user_public
):
    """Тест сохранения всех типов согласий."""
    mock_create_privacy_consent.return_value = None
    mock_cache_service.invalidate = AsyncMock()

    consent_data = PrivacyConsentRequest(
        personal_data=True,
        cookies=True,
        marketing=True,
    )

    await PrivacyService.save_consent(mock_request, mock_session, user_public, consent_data)

    assert mock_create_privacy_consent.call_count == 3
    assert mock_cache_service.invalidate.call_count == 3  # invalidate вызывается для каждого типа согласия
    mock_cache_service.invalidate.assert_called_with(1)


@pytest.mark.asyncio
@patch("src.app.core.services.privacy_service.create_privacy_consent")
@patch("src.app.core.services.privacy_service.ConsentCacheService")
async def test_save_consent_only_personal_data(
    mock_cache_service, mock_create_privacy_consent, mock_request, mock_session, user_public
):
    """Тест сохранения только согласия на персональные данные."""
    mock_create_privacy_consent.return_value = None
    mock_cache_service.invalidate = AsyncMock()

    consent_data = PrivacyConsentRequest(
        personal_data=True,
        cookies=False,
        marketing=False,
    )

    await PrivacyService.save_consent(mock_request, mock_session, user_public, consent_data)

    assert mock_create_privacy_consent.call_count == 1
    first_call = mock_create_privacy_consent.call_args_list[0]
    assert first_call[1]["consent_type"] == ConsentType.PERSONAL_DATA


@pytest.mark.asyncio
@patch("src.app.core.services.privacy_service.create_privacy_consent")
@patch("src.app.core.services.privacy_service.get_client_ip")
async def test_save_consent_no_client_ip_in_state(
    mock_get_client_ip, mock_create_privacy_consent, mock_request, mock_session, user_public, consent_data
):
    """Тест когда client_ip не в request.state."""
    mock_create_privacy_consent.return_value = None
    mock_get_client_ip.return_value = "10.0.0.1"
    mock_request.state.client_ip = None

    await PrivacyService.save_consent(mock_request, mock_session, user_public, consent_data)

    first_call = mock_create_privacy_consent.call_args_list[0]
    assert first_call[1]["ip_address"] == "10.0.0.1"


@pytest.mark.asyncio
@patch("src.app.core.services.privacy_service.create_privacy_consent")
@patch("src.app.core.services.privacy_service.ConsentCacheService")
async def test_save_consent_no_user_agent(
    mock_cache_service, mock_create_privacy_consent, mock_request, mock_session, user_public, consent_data
):
    """Тест когда user-agent отсутствует."""
    mock_create_privacy_consent.return_value = None
    mock_cache_service.invalidate = AsyncMock()
    mock_request.headers = {}

    await PrivacyService.save_consent(mock_request, mock_session, user_public, consent_data)

    first_call = mock_create_privacy_consent.call_args_list[0]
    assert first_call[1]["user_agent"] == "unknown"


@pytest.mark.asyncio
@patch("src.app.core.services.privacy_service.create_privacy_consent")
@patch("src.app.core.services.privacy_service.ConsentCacheService")
async def test_save_consent_no_redis_session(
    mock_cache_service, mock_create_privacy_consent, mock_request, mock_session, user_public, consent_data
):
    """Тест когда redis_session отсутствует."""
    mock_create_privacy_consent.return_value = None
    mock_cache_service.invalidate = AsyncMock()
    mock_request.scope = {}

    await PrivacyService.save_consent(mock_request, mock_session, user_public, consent_data)

    # Для авторизованного пользователя session_id должен быть None
    first_call = mock_create_privacy_consent.call_args_list[0]
    assert first_call[1]["session_id"] is None


# --- get_consent_status ---


@pytest.mark.asyncio
@patch("src.app.core.services.privacy_service.has_user_consent")
@patch("src.app.core.services.privacy_service.get_user_consents")
async def test_get_consent_status_authorized_user(
    mock_get_user_consents, mock_has_user_consent, mock_request, mock_session, user_public
):
    """Тест получения статуса согласия для авторизованного пользователя."""
    mock_consents = [MagicMock()]
    mock_consents[0].granted_at = datetime(2024, 1, 1, 12, 0, 0)
    mock_get_user_consents.return_value = mock_consents
    mock_has_user_consent.side_effect = [True, True, False]

    result = await PrivacyService.get_consent_status(mock_request, mock_session, user_public)

    assert result["personal_data"] is True
    assert result["cookies"] is True
    assert result["marketing"] is False
    assert result["has_consent"] is True
    assert result["last_updated"] == datetime(2024, 1, 1, 12, 0, 0)


@pytest.mark.asyncio
@patch("src.app.core.services.privacy_service.has_session_consent")
@patch("src.app.core.services.privacy_service.get_session_consents")
async def test_get_consent_status_unauthorized_user(
    mock_get_session_consents, mock_has_session_consent, mock_request, mock_session
):
    """Тест получения статуса согласия для неавторизованного пользователя."""
    mock_consents = [MagicMock()]
    mock_consents[0].granted_at = datetime(2024, 1, 1, 12, 0, 0)
    mock_get_session_consents.return_value = mock_consents
    mock_has_session_consent.side_effect = [False, True, False]

    result = await PrivacyService.get_consent_status(mock_request, mock_session, None)

    assert result["personal_data"] is False
    assert result["cookies"] is True
    assert result["marketing"] is False
    assert result["has_consent"] is True


@pytest.mark.asyncio
@patch("src.app.core.services.privacy_service.has_user_consent")
@patch("src.app.core.services.privacy_service.get_user_consents")
async def test_get_consent_status_no_consents(
    mock_get_user_consents, mock_has_user_consent, mock_request, mock_session, user_public
):
    """Тест получения статуса когда нет согласий."""
    mock_get_user_consents.return_value = []
    mock_has_user_consent.side_effect = [False, False, False]

    result = await PrivacyService.get_consent_status(mock_request, mock_session, user_public)

    assert result["has_consent"] is False
    assert result["last_updated"] is None


@pytest.mark.asyncio
@patch("src.app.core.services.privacy_service.has_user_consent")
@patch("src.app.core.services.privacy_service.get_user_consents")
async def test_get_consent_status_authorized_user_checks_all_types(
    mock_get_user_consents, mock_has_user_consent, mock_request, mock_session, user_public
):
    """Тест что проверяются все типы согласий для авторизованного пользователя."""
    mock_get_user_consents.return_value = []
    mock_has_user_consent.side_effect = [True, False, True]

    await PrivacyService.get_consent_status(mock_request, mock_session, user_public)

    assert mock_has_user_consent.call_count == 3
    calls = mock_has_user_consent.call_args_list
    assert calls[0][0][2] == ConsentType.PERSONAL_DATA
    assert calls[1][0][2] == ConsentType.COOKIES
    assert calls[2][0][2] == ConsentType.MARKETING


@pytest.mark.asyncio
@patch("src.app.core.services.privacy_service.has_session_consent")
@patch("src.app.core.services.privacy_service.get_session_consents")
async def test_get_consent_status_unauthorized_user_checks_all_types(
    mock_get_session_consents, mock_has_session_consent, mock_request, mock_session
):
    """Тест что проверяются все типы согласий для неавторизованного пользователя."""
    mock_get_session_consents.return_value = []
    mock_has_session_consent.side_effect = [False, False, False]

    await PrivacyService.get_consent_status(mock_request, mock_session, None)

    assert mock_has_session_consent.call_count == 3
    calls = mock_has_session_consent.call_args_list
    assert calls[0][0][2] == ConsentType.PERSONAL_DATA
    assert calls[1][0][2] == ConsentType.COOKIES
    assert calls[2][0][2] == ConsentType.MARKETING


# --- get_privacy_service ---


def test_get_privacy_service():
    """Тест что get_privacy_service возвращает экземпляр PrivacyService."""
    service = get_privacy_service()
    
    assert isinstance(service, PrivacyService)
