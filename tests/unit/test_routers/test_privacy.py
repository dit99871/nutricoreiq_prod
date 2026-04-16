"""
Тесты для privacy router.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import Request

from src.app.core.schemas.privacy import (
    ConsentStatusResponse,
    PrivacyConsentRequest,
    PrivacyConsentResponse,
)
from src.app.core.schemas.user import UserPublic


@pytest.fixture
def mock_request():
    """Создает мок для Request."""
    request = MagicMock(spec=Request)
    request.state = MagicMock()
    return request


@pytest.fixture
def mock_db_session():
    """Создает мок для DB session."""
    session = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    return session


@pytest.fixture
def mock_privacy_service():
    """Создает мок для PrivacyService."""
    service = AsyncMock()
    return service


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


# --- save_privacy_consent ---


@pytest.mark.asyncio
async def test_save_privacy_consent_success_authorized(
    mock_request, mock_db_session, mock_privacy_service, user_public, consent_data
):
    """Тест успешного сохранения согласия для авторизованного пользователя."""
    from src.app.routers.privacy import save_privacy_consent

    mock_privacy_service.save_consent.return_value = None

    result = await save_privacy_consent(
        mock_request, consent_data, mock_db_session, user_public, mock_privacy_service
    )

    assert isinstance(result, PrivacyConsentResponse)
    assert result.success is True
    assert result.message == "Согласие успешно сохранено"
    mock_privacy_service.save_consent.assert_called_once_with(
        request=mock_request,
        session=mock_db_session,
        user=user_public,
        consent_data=consent_data,
    )
    mock_db_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_save_privacy_consent_success_unauthorized(
    mock_request, mock_db_session, mock_privacy_service, consent_data
):
    """Тест успешного сохранения согласия для неавторизованного пользователя."""
    from src.app.routers.privacy import save_privacy_consent

    mock_privacy_service.save_consent.return_value = None

    result = await save_privacy_consent(
        mock_request, consent_data, mock_db_session, None, mock_privacy_service
    )

    assert isinstance(result, PrivacyConsentResponse)
    assert result.success is True
    mock_privacy_service.save_consent.assert_called_once_with(
        request=mock_request,
        session=mock_db_session,
        user=None,
        consent_data=consent_data,
    )
    mock_db_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_save_privacy_consent_error_rollback(
    mock_request, mock_db_session, mock_privacy_service, user_public, consent_data
):
    """Тест отката при ошибке сохранения согласия."""
    from src.app.routers.privacy import save_privacy_consent

    mock_privacy_service.save_consent.side_effect = Exception("Database error")

    with pytest.raises(Exception) as exc_info:
        await save_privacy_consent(
            mock_request, consent_data, mock_db_session, user_public, mock_privacy_service
        )

    assert "Database error" in str(exc_info.value)
    mock_db_session.rollback.assert_called_once()


# --- get_consent_status ---


@pytest.mark.asyncio
async def test_get_consent_status_success_authorized(
    mock_request, mock_db_session, mock_privacy_service, user_public
):
    """Тест успешного получения статуса согласия для авторизованного пользователя."""
    from src.app.routers.privacy import get_consent_status

    mock_privacy_service.get_consent_status.return_value = {
        "personal_data": True,
        "cookies": True,
        "marketing": False,
        "has_consent": True,
    }

    result = await get_consent_status(
        mock_request, mock_db_session, user_public, mock_privacy_service
    )

    assert isinstance(result, ConsentStatusResponse)
    assert result.personal_data is True
    assert result.cookies is True
    assert result.marketing is False
    assert result.has_consent is True
    mock_privacy_service.get_consent_status.assert_called_once_with(
        request=mock_request,
        session=mock_db_session,
        user=user_public,
    )


@pytest.mark.asyncio
async def test_get_consent_status_success_unauthorized(
    mock_request, mock_db_session, mock_privacy_service
):
    """Тест успешного получения статуса согласия для неавторизованного пользователя."""
    from src.app.routers.privacy import get_consent_status

    mock_privacy_service.get_consent_status.return_value = {
        "personal_data": False,
        "cookies": False,
        "marketing": False,
        "has_consent": False,
    }

    result = await get_consent_status(
        mock_request, mock_db_session, None, mock_privacy_service
    )

    assert isinstance(result, ConsentStatusResponse)
    assert result.personal_data is False
    assert result.cookies is False
    assert result.marketing is False
    assert result.has_consent is False


@pytest.mark.asyncio
async def test_get_consent_status_error_returns_default(
    mock_request, mock_db_session, mock_privacy_service, user_public
):
    """Тест возврата значений по умолчанию при ошибке."""
    from src.app.routers.privacy import get_consent_status

    mock_privacy_service.get_consent_status.side_effect = Exception("Service error")

    result = await get_consent_status(
        mock_request, mock_db_session, user_public, mock_privacy_service
    )

    assert isinstance(result, ConsentStatusResponse)
    assert result.personal_data is False
    assert result.cookies is False
    assert result.marketing is False
    assert result.has_consent is False
