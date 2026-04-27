"""
Тесты для Pydantic-схем согласий на обработку персональных данных.
"""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from src.app.core.schemas.privacy import (
    ConsentStatusResponse,
    PrivacyConsentInfo,
    PrivacyConsentRequest,
    PrivacyConsentResponse,
)


# ─── PrivacyConsentRequest ───────────────────────────────────────────────────


class TestPrivacyConsentRequest:
    """Тесты для PrivacyConsentRequest."""

    def test_minimal_valid_request(self):
        """Минимальный валидный запрос — только personal_data."""
        req = PrivacyConsentRequest(personal_data=True)
        assert req.personal_data is True
        assert req.cookies is False
        assert req.marketing is False
        assert req.timestamp is None

    def test_full_request_with_all_fields(self):
        """Полный запрос со всеми полями."""
        req = PrivacyConsentRequest(
            personal_data=True,
            cookies=True,
            marketing=True,
            timestamp="2024-01-15T10:30:00",
        )
        assert req.cookies is True
        assert req.marketing is True
        assert req.timestamp == "2024-01-15T10:30:00"

    def test_personal_data_required(self):
        """personal_data обязательное поле."""
        with pytest.raises(ValidationError):
            PrivacyConsentRequest()

    def test_defaults_for_optional_fields(self):
        """Необязательные поля имеют значения по умолчанию."""
        req = PrivacyConsentRequest(personal_data=False)
        assert req.cookies is False
        assert req.marketing is False
        assert req.timestamp is None

    def test_personal_data_false_valid(self):
        """personal_data=False является допустимым значением."""
        req = PrivacyConsentRequest(personal_data=False)
        assert req.personal_data is False


# ─── PrivacyConsentResponse ──────────────────────────────────────────────────


class TestPrivacyConsentResponse:
    """Тесты для PrivacyConsentResponse."""

    def test_success_response(self):
        """Успешный ответ."""
        resp = PrivacyConsentResponse(success=True, message="Согласие сохранено")
        assert resp.success is True
        assert resp.message == "Согласие сохранено"

    def test_failure_response(self):
        """Ответ об ошибке."""
        resp = PrivacyConsentResponse(success=False, message="Ошибка сохранения")
        assert resp.success is False

    def test_required_fields(self):
        """Оба поля обязательны."""
        with pytest.raises(ValidationError):
            PrivacyConsentResponse(success=True)  # нет message

        with pytest.raises(ValidationError):
            PrivacyConsentResponse(message="ok")  # нет success


# ─── ConsentStatusResponse ───────────────────────────────────────────────────


class TestConsentStatusResponse:
    """Тесты для ConsentStatusResponse."""

    def test_full_consent(self):
        """Все согласия получены."""
        resp = ConsentStatusResponse(
            personal_data=True,
            cookies=True,
            marketing=False,
            has_consent=True,
            last_updated=None,
        )
        assert resp.personal_data is True
        assert resp.has_consent is True
        assert resp.last_updated is None

    def test_no_consent(self):
        """Нет ни одного согласия."""
        resp = ConsentStatusResponse(
            personal_data=False,
            cookies=False,
            marketing=False,
            has_consent=False,
        )
        assert resp.has_consent is False

    def test_with_last_updated(self):
        """Поле last_updated принимает datetime."""
        now = datetime.now(timezone.utc)
        resp = ConsentStatusResponse(
            personal_data=True,
            cookies=False,
            marketing=False,
            has_consent=True,
            last_updated=now,
        )
        assert resp.last_updated == now

    def test_required_fields_missing(self):
        """Обязательные поля должны присутствовать."""
        with pytest.raises(ValidationError):
            ConsentStatusResponse(has_consent=True)


# ─── PrivacyConsentInfo ──────────────────────────────────────────────────────


class TestPrivacyConsentInfo:
    """Тесты для PrivacyConsentInfo."""

    def test_valid_info(self):
        """Валидный объект информации о согласии."""
        now = datetime.now(timezone.utc)
        info = PrivacyConsentInfo(
            id=1,
            consent_type="personal_data",
            is_granted=True,
            granted_at=now,
            policy_version="1.0",
            ip_address="127.0.0.1",
            user_agent="Mozilla/5.0",
        )
        assert info.id == 1
        assert info.consent_type == "personal_data"
        assert info.is_granted is True
        assert info.policy_version == "1.0"

    def test_missing_required_field(self):
        """Отсутствие обязательного поля → ValidationError."""
        with pytest.raises(ValidationError):
            PrivacyConsentInfo(
                id=1,
                consent_type="cookies",
                # нет is_granted и других обязательных полей
            )

    def test_is_granted_false(self):
        """is_granted может быть False (отозванное согласие)."""
        now = datetime.now(timezone.utc)
        info = PrivacyConsentInfo(
            id=2,
            consent_type="marketing",
            is_granted=False,
            granted_at=now,
            policy_version="2.0",
            ip_address="10.0.0.1",
            user_agent="Chrome/120",
        )
        assert info.is_granted is False