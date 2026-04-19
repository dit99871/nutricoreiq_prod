"""
Тесты для ORM-модели и enum согласий на обработку персональных данных.
"""

import pytest

from src.app.core.models.privacy_consent import ConsentType


class TestConsentType:
    """Тесты для перечисления ConsentType."""

    @pytest.mark.parametrize("consent,value", [
        (ConsentType.PERSONAL_DATA, "personal_data"),
        (ConsentType.COOKIES, "cookies"),
        (ConsentType.MARKETING, "marketing"),
    ])
    def test_consent_type_values(self, consent, value):
        """Каждый тип согласия имеет правильное строковое значение."""
        assert consent.value == value

    def test_consent_type_from_value(self):
        """Создание из строкового значения."""
        assert ConsentType("personal_data") == ConsentType.PERSONAL_DATA
        assert ConsentType("cookies") == ConsentType.COOKIES
        assert ConsentType("marketing") == ConsentType.MARKETING

    def test_consent_type_invalid_raises(self):
        """Неверное значение → ValueError."""
        with pytest.raises(ValueError):
            ConsentType("terms_of_service")

    def test_consent_type_all_members(self):
        """Перечисление содержит ровно 3 типа."""
        assert len(ConsentType) == 3

    def test_consent_type_uniqueness(self):
        """Все значения уникальны."""
        values = [c.value for c in ConsentType]
        assert len(values) == len(set(values))