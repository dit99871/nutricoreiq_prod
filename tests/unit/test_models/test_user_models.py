"""
Тесты для ORM-моделей и перечислений пользователя.
Покрывает: UserRole, KFALevel, GoalType enum + поведение KFALevel.__str__.
"""

import pytest

from src.app.core.models.user import GoalType, KFALevel, UserRole


# ─── UserRole ─────────────────────────────────────────────────────────────────


class TestUserRole:
    """Тесты для перечисления UserRole."""

    def test_user_role_values(self):
        """Проверяет наличие всех ролей."""
        assert UserRole.USER.value == "user"
        assert UserRole.ADMIN.value == "admin"
        assert UserRole.MODERATOR.value == "moderator"

    def test_user_role_from_value(self):
        """Создание из строкового значения."""
        assert UserRole("user") == UserRole.USER
        assert UserRole("admin") == UserRole.ADMIN
        assert UserRole("moderator") == UserRole.MODERATOR

    def test_user_role_invalid_raises(self):
        """Неверное значение → ValueError."""
        with pytest.raises(ValueError):
            UserRole("superuser")

    def test_user_role_all_members(self):
        """Перечисление содержит ровно 3 роли."""
        assert len(UserRole) == 3

    def test_user_role_comparison(self):
        """Роли сравниваются по identity."""
        assert UserRole.USER is UserRole.USER
        assert UserRole.ADMIN is not UserRole.USER


# ─── KFALevel ─────────────────────────────────────────────────────────────────


class TestKFALevel:
    """Тесты для перечисления KFALevel."""

    @pytest.mark.parametrize("level,value", [
        (KFALevel.VERY_LOW, "1.2"),
        (KFALevel.LOW, "1.375"),
        (KFALevel.MEDIUM, "1.55"),
        (KFALevel.HIGH, "1.725"),
        (KFALevel.VERY_HIGH, "1.9"),
    ])
    def test_kfa_level_values(self, level, value):
        """Каждый уровень имеет правильное строковое значение."""
        assert level.value == value

    def test_kfa_level_from_value(self):
        """Создание из строкового значения."""
        assert KFALevel("1.2") == KFALevel.VERY_LOW
        assert KFALevel("1.9") == KFALevel.VERY_HIGH

    def test_kfa_level_invalid_raises(self):
        """Неверное значение → ValueError."""
        with pytest.raises(ValueError):
            KFALevel("2.0")

    def test_kfa_level_all_members(self):
        """Перечисление содержит ровно 5 уровней."""
        assert len(KFALevel) == 5

    @pytest.mark.parametrize("level,expected_str", [
        (KFALevel.VERY_LOW, "Очень низкий"),
        (KFALevel.LOW, "Низкий"),
        (KFALevel.MEDIUM, "Средний"),
        (KFALevel.HIGH, "Высокий"),
        (KFALevel.VERY_HIGH, "Очень высокий"),
    ])
    def test_kfa_level_str_representation(self, level, expected_str):
        """__str__ возвращает читаемое название уровня."""
        assert str(level) == expected_str

    def test_kfa_levels_are_ascending(self):
        """Числовые значения KFA возрастают от VERY_LOW до VERY_HIGH."""
        levels = [KFALevel.VERY_LOW, KFALevel.LOW, KFALevel.MEDIUM, KFALevel.HIGH, KFALevel.VERY_HIGH]
        values = [float(l.value) for l in levels]
        assert values == sorted(values)

    def test_kfa_level_uniqueness(self):
        """Все значения уникальны."""
        values = [l.value for l in KFALevel]
        assert len(values) == len(set(values))


# ─── GoalType ─────────────────────────────────────────────────────────────────


class TestGoalType:
    """Тесты для перечисления GoalType."""

    @pytest.mark.parametrize("goal,value", [
        (GoalType.LOSE_WEIGHT, "Снижение веса"),
        (GoalType.GAIN_WEIGHT, "Увеличение веса"),
        (GoalType.MAINTAIN_WEIGHT, "Поддержание веса"),
    ])
    def test_goal_type_values(self, goal, value):
        """Каждый тип цели имеет правильное строковое значение."""
        assert goal.value == value

    def test_goal_type_from_value(self):
        """Создание из строкового значения."""
        assert GoalType("Снижение веса") == GoalType.LOSE_WEIGHT
        assert GoalType("Увеличение веса") == GoalType.GAIN_WEIGHT
        assert GoalType("Поддержание веса") == GoalType.MAINTAIN_WEIGHT

    def test_goal_type_invalid_raises(self):
        """Неверное значение → ValueError."""
        with pytest.raises(ValueError):
            GoalType("Набрать мышцы")

    def test_goal_type_all_members(self):
        """Перечисление содержит ровно 3 типа."""
        assert len(GoalType) == 3

    def test_goal_type_uniqueness(self):
        """Все значения уникальны."""
        values = [g.value for g in GoalType]
        assert len(values) == len(set(values))