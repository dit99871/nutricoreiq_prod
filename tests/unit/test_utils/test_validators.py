"""
Тесты для утилит валидации и преобразования данных (validators.py).
Покрывает: validate_password_strength, coerce_kfa, coerce_goal.
"""

import pytest

from src.app.core.models.user import GoalType, KFALevel
from src.app.core.utils.validators import coerce_goal, coerce_kfa, validate_password_strength


# ─── validate_password_strength ──────────────────────────────────────────────


class TestValidatePasswordStrength:
    """Тесты для validate_password_strength."""

    def test_valid_password_returns_unchanged(self):
        """Валидный пароль возвращается без изменений."""
        password = "StrongP@ss1"
        assert validate_password_strength(password) == password

    def test_missing_uppercase_raises(self):
        """Нет прописных букв — ValueError."""
        with pytest.raises(ValueError, match="прописные"):
            validate_password_strength("weakp@ss1")

    def test_missing_lowercase_raises(self):
        """Нет строчных букв — ValueError."""
        with pytest.raises(ValueError, match="строчные"):
            validate_password_strength("STRONGP@SS1")

    def test_missing_digit_raises(self):
        """Нет цифр — ValueError."""
        with pytest.raises(ValueError, match="цифры"):
            validate_password_strength("StrongP@ssword")

    def test_missing_special_char_raises(self):
        """Нет спецсимволов — ValueError."""
        with pytest.raises(ValueError, match="спецсимволы"):
            validate_password_strength("StrongPass1")

    def test_all_conditions_met_short(self):
        """Минимальный пароль со всеми условиями."""
        assert validate_password_strength("aA1!") == "aA1!"

    def test_all_conditions_met_long(self):
        """Длинный пароль проходит валидацию."""
        password = "MyStr0ng&SecurePassword#2024"
        assert validate_password_strength(password) == password

    @pytest.mark.parametrize("special_char", ["!", "@", "#", "$", "%", "^", "&", "*", "(", ")", "-", "_"])
    def test_various_special_chars_accepted(self, special_char):
        """Разные спецсимволы принимаются."""
        password = f"ValidP4ss{special_char}"
        assert validate_password_strength(password) == password

    def test_only_digits_and_special_raises(self):
        """Только цифры и спецсимволы — нет букв."""
        with pytest.raises(ValueError):
            validate_password_strength("1234!@#$5678")

    def test_unicode_letters_count_as_letters(self):
        """Unicode буквы считаются буквами."""
        # содержит строчные (a), прописные (A), цифры (1), спецсимвол (!)
        assert validate_password_strength("aA1!Ёж") is not None


# ─── coerce_kfa ──────────────────────────────────────────────────────────────


class TestCoerceKfa:
    """Тесты для coerce_kfa."""

    def test_none_returns_none(self):
        """None → None."""
        assert coerce_kfa(None) is None

    def test_empty_string_returns_none(self):
        """Пустая строка → None."""
        assert coerce_kfa("") is None

    def test_kfa_instance_returned_as_is(self):
        """Экземпляр KFALevel возвращается без изменений."""
        kfa = KFALevel.MEDIUM
        assert coerce_kfa(kfa) is kfa

    @pytest.mark.parametrize("value,expected", [
        ("1.2", KFALevel.VERY_LOW),
        ("1.375", KFALevel.LOW),
        ("1.55", KFALevel.MEDIUM),
        ("1.725", KFALevel.HIGH),
        ("1.9", KFALevel.VERY_HIGH),
    ])
    def test_valid_string_values(self, value, expected):
        """Строковые значения KFA конвертируются корректно."""
        assert coerce_kfa(value) == expected

    def test_invalid_string_raises(self):
        """Неверная строка → ValueError."""
        with pytest.raises(ValueError, match="Недопустимое значение KFA"):
            coerce_kfa("2.0")

    def test_invalid_string_garbage_raises(self):
        """Мусорная строка → ValueError."""
        with pytest.raises(ValueError, match="Недопустимое значение KFA"):
            coerce_kfa("not_a_kfa_level")

    def test_numeric_float_raises(self):
        """Некорректный числовой float → ValueError (не входит в допустимые значения)."""
        with pytest.raises(ValueError):
            coerce_kfa(99.9)

    def test_all_kfa_levels_via_string(self):
        """Все допустимые уровни KFA конвертируются из строк."""
        for level in KFALevel:
            result = coerce_kfa(level.value)
            assert result == level


# ─── coerce_goal ─────────────────────────────────────────────────────────────


class TestCoerceGoal:
    """Тесты для coerce_goal."""

    def test_none_returns_none(self):
        """None → None."""
        assert coerce_goal(None) is None

    def test_empty_string_returns_none(self):
        """Пустая строка → None."""
        assert coerce_goal("") is None

    def test_goal_instance_returned_as_is(self):
        """Экземпляр GoalType возвращается без изменений."""
        goal = GoalType.LOSE_WEIGHT
        assert coerce_goal(goal) is goal

    @pytest.mark.parametrize("value,expected", [
        ("Снижение веса", GoalType.LOSE_WEIGHT),
        ("Увеличение веса", GoalType.GAIN_WEIGHT),
        ("Поддержание веса", GoalType.MAINTAIN_WEIGHT),
    ])
    def test_valid_string_values(self, value, expected):
        """Строковые значения GoalType конвертируются корректно."""
        assert coerce_goal(value) == expected

    def test_invalid_string_raises(self):
        """Неверная строка → ValueError."""
        with pytest.raises(ValueError, match="Недопустимое значение goal"):
            coerce_goal("Похудеть")

    def test_garbage_value_raises(self):
        """Мусорное значение → ValueError."""
        with pytest.raises(ValueError):
            coerce_goal("not_a_goal")

    def test_numeric_value_raises(self):
        """Число → ValueError."""
        with pytest.raises(ValueError):
            coerce_goal(42)

    def test_all_goal_types_via_string(self):
        """Все типы целей конвертируются из строк."""
        for goal in GoalType:
            result = coerce_goal(goal.value)
            assert result == goal