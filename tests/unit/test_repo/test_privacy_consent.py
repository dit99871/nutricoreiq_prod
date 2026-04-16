import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.exc import SQLAlchemyError

from src.app.core.exceptions import DatabaseError
from src.app.core.models.privacy_consent import ConsentType, PrivacyConsent
from src.app.core.repo.privacy_consent import (
    create_privacy_consent,
    get_session_consents,
    get_user_consents,
    has_session_consent,
    has_user_consent,
)


@pytest.fixture
def mock_session():
    """Создает мок асинхронной сессии SQLAlchemy."""
    session = MagicMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    session.rollback = AsyncMock()
    session.execute = AsyncMock()
    return session


@pytest.fixture
def sample_privacy_consent():
    """Создает образец записи согласия."""
    return PrivacyConsent(
        id=1,
        user_id=123,
        session_id=None,
        ip_address="192.168.1.1",
        user_agent="Mozilla/5.0",
        consent_type=ConsentType.PERSONAL_DATA,
        is_granted=True,
        policy_version="1.0",
        granted_at=datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None),
    )


class TestCreatePrivacyConsent:
    """Тесты для функции create_privacy_consent."""

    @pytest.mark.asyncio
    async def test_create_privacy_consent_success_user(self, mock_session):
        """Тест успешного создания согласия для авторизованного пользователя."""

        def mock_add(consent):
            consent.id = 1
            return consent

        mock_session.add.side_effect = mock_add

        with patch("src.app.core.repo.privacy_consent.log") as mock_log:
            result = await create_privacy_consent(
                session=mock_session,
                user_id=123,
                session_id=None,
                ip_address="192.168.1.1",
                user_agent="Mozilla/5.0",
                consent_type=ConsentType.PERSONAL_DATA,
                is_granted=True,
                policy_version="1.0",
            )

        assert isinstance(result, PrivacyConsent)
        assert result.user_id == 123
        assert result.session_id is None
        assert result.ip_address == "192.168.1.1"
        assert result.user_agent == "Mozilla/5.0"
        assert result.consent_type == ConsentType.PERSONAL_DATA
        assert result.is_granted is True
        assert result.policy_version == "1.0"

        mock_session.add.assert_called_once()
        mock_session.flush.assert_awaited_once()
        mock_log.info.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_privacy_consent_success_session(self, mock_session):
        """Тест успешного создания согласия для сессии."""

        def mock_add(consent):
            consent.id = 2
            return consent

        mock_session.add.side_effect = mock_add

        with patch("src.app.core.repo.privacy_consent.log") as mock_log:
            result = await create_privacy_consent(
                session=mock_session,
                user_id=None,
                session_id="session_123",
                ip_address="192.168.1.2",
                user_agent="Chrome/91.0",
                consent_type=ConsentType.COOKIES,
                is_granted=False,
            )

        assert isinstance(result, PrivacyConsent)
        assert result.user_id is None
        assert result.session_id == "session_123"
        assert result.consent_type == ConsentType.COOKIES
        assert result.is_granted is False
        assert result.policy_version == "1.0"  # значение по умолчанию

        mock_session.add.assert_called_once()
        mock_session.flush.assert_awaited_once()
        mock_log.info.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_privacy_consent_database_error(self, mock_session):
        """Тест обработки ошибки базы данных."""
        mock_session.flush.side_effect = SQLAlchemyError("Database error")

        with patch("src.app.core.repo.privacy_consent.log") as mock_log:
            with pytest.raises(DatabaseError) as exc_info:
                await create_privacy_consent(
                    session=mock_session,
                    user_id=123,
                    session_id=None,
                    ip_address="192.168.1.1",
                    user_agent="Mozilla/5.0",
                    consent_type=ConsentType.PERSONAL_DATA,
                    is_granted=True,
                )

        assert exc_info.value.message == "Ошибка при сохранении согласия"
        mock_session.rollback.assert_awaited_once()
        mock_log.error.assert_called_once()


class TestHasUserConsent:
    """Тесты для функции has_user_consent."""

    @pytest.mark.asyncio
    async def test_has_user_consent_true(self, mock_session, sample_privacy_consent):
        """Тест: у пользователя есть согласие."""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_privacy_consent
        mock_session.execute.return_value = mock_result

        result = await has_user_consent(
            session=mock_session,
            user_id=123,
            consent_type=ConsentType.PERSONAL_DATA,
        )

        assert result is True
        mock_session.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_has_user_consent_false(self, mock_session):
        """Тест: у пользователя нет согласия."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await has_user_consent(
            session=mock_session,
            user_id=123,
            consent_type=ConsentType.PERSONAL_DATA,
        )

        assert result is False
        mock_session.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_has_user_consent_default_type(
        self, mock_session, sample_privacy_consent
    ):
        """Тест: используется тип согласия по умолчанию."""

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_privacy_consent
        mock_session.execute.return_value = mock_result

        result = await has_user_consent(session=mock_session, user_id=123)

        assert result is True

    @pytest.mark.asyncio
    async def test_has_user_consent_database_error(self, mock_session):
        """Тест обработки ошибки базы данных."""

        mock_session.execute.side_effect = SQLAlchemyError("Database error")

        with patch("src.app.core.repo.privacy_consent.log") as mock_log:
            result = await has_user_consent(
                session=mock_session,
                user_id=123,
                consent_type=ConsentType.PERSONAL_DATA,
            )

        assert result is False
        mock_log.error.assert_called_once()


class TestHasSessionConsent:
    """Тесты для функции has_session_consent."""

    @pytest.mark.asyncio
    async def test_has_session_consent_true(self, mock_session, sample_privacy_consent):
        """Тест: у сессии есть согласие."""

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_privacy_consent
        mock_session.execute.return_value = mock_result

        result = await has_session_consent(
            session=mock_session,
            session_id="session_123",
            consent_type=ConsentType.COOKIES,
        )

        assert result is True
        mock_session.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_has_session_consent_false(self, mock_session):
        """Тест: у сессии нет согласия."""

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await has_session_consent(
            session=mock_session,
            session_id="session_123",
            consent_type=ConsentType.COOKIES,
        )

        assert result is False
        mock_session.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_has_session_consent_default_type(
        self, mock_session, sample_privacy_consent
    ):
        """Тест: используется тип согласия по умолчанию."""

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_privacy_consent
        mock_session.execute.return_value = mock_result

        result = await has_session_consent(
            session=mock_session, session_id="session_123"
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_has_session_consent_database_error(self, mock_session):
        """Тест обработки ошибки базы данных."""

        mock_session.execute.side_effect = SQLAlchemyError("Database error")

        with patch("src.app.core.repo.privacy_consent.log") as mock_log:
            result = await has_session_consent(
                session=mock_session,
                session_id="session_123",
                consent_type=ConsentType.COOKIES,
            )

        assert result is False
        mock_log.error.assert_called_once()


class TestGetUserConsents:
    """Тесты для функции get_user_consents."""

    @pytest.mark.asyncio
    async def test_get_user_consents_success(self, mock_session):
        """Тест успешного получения согласий пользователя."""

        consent1 = PrivacyConsent(
            id=1, user_id=123, consent_type=ConsentType.PERSONAL_DATA
        )
        consent2 = PrivacyConsent(id=2, user_id=123, consent_type=ConsentType.COOKIES)

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [consent1, consent2]
        mock_session.execute.return_value = mock_result

        result = await get_user_consents(session=mock_session, user_id=123)

        assert len(result) == 2
        assert result[0].user_id == 123
        assert result[1].user_id == 123
        mock_session.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_user_consents_empty(self, mock_session):
        """Тест: у пользователя нет согласий."""

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        result = await get_user_consents(session=mock_session, user_id=123)

        assert len(result) == 0
        mock_session.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_user_consents_database_error(self, mock_session):
        """Тест обработки ошибки базы данных."""

        mock_session.execute.side_effect = SQLAlchemyError("Database error")

        with patch("src.app.core.repo.privacy_consent.log") as mock_log:
            result = await get_user_consents(session=mock_session, user_id=123)

        assert result == []
        mock_log.error.assert_called_once()


class TestGetSessionConsents:
    """Тесты для функции get_session_consents."""

    @pytest.mark.asyncio
    async def test_get_session_consents_success(self, mock_session):
        """Тест успешного получения согласий сессии."""

        consent1 = PrivacyConsent(
            id=1, session_id="session_123", consent_type=ConsentType.PERSONAL_DATA
        )
        consent2 = PrivacyConsent(
            id=2, session_id="session_123", consent_type=ConsentType.COOKIES
        )

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [consent1, consent2]
        mock_session.execute.return_value = mock_result

        result = await get_session_consents(
            session=mock_session, session_id="session_123"
        )

        assert len(result) == 2
        assert result[0].session_id == "session_123"
        assert result[1].session_id == "session_123"
        mock_session.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_session_consents_empty(self, mock_session):
        """Тест: у сессии нет согласий."""

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        result = await get_session_consents(
            session=mock_session, session_id="session_123"
        )

        assert len(result) == 0
        mock_session.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_session_consents_database_error(self, mock_session):
        """Тест обработки ошибки базы данных."""

        mock_session.execute.side_effect = SQLAlchemyError("Database error")

        with patch("src.app.core.repo.privacy_consent.log") as mock_log:
            result = await get_session_consents(
                session=mock_session, session_id="session_123"
            )

        assert result == []
        mock_log.error.assert_called_once()


class TestConsentType:
    """Тесты для enum ConsentType."""

    def test_consent_type_values(self):
        """Тест значений enum ConsentType."""
        assert ConsentType.PERSONAL_DATA.value == "personal_data"
        assert ConsentType.COOKIES.value == "cookies"
        assert ConsentType.MARKETING.value == "marketing"

    def test_consent_type_uniqueness(self):
        """Тест уникальности значений enum."""
        values = [consent_type.value for consent_type in ConsentType]
        assert len(values) == len(set(values))
