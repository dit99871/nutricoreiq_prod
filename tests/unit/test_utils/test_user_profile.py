"""
Тесты для доменной логики расчёта BMR и TDEE.
"""

import pytest
from src.app.core.utils.user_profile import calculate_bmr, calculate_tdee
from src.app.core.schemas.user import UserProfile
from src.app.core.models.user import KFALevel, GoalType


@pytest.fixture
def male_user_profile():
    """Мужчина, 30 лет, 80 кг, 180 см, средняя активность"""

    return UserProfile(
        id=1,
        uid="test-uid-male",
        username="testuser_male",
        email="male@example.com",
        gender="male",
        age=30,
        weight=80.0,
        height=180.0,
        kfa=KFALevel.MEDIUM,
        goal=GoalType.MAINTAIN_WEIGHT,
        created_at="2024-01-01T00:00:00",
        is_subscribed=True,
    )


@pytest.fixture
def female_user_profile():
    """Женщина, 25 лет, 60 кг, 165 см, низкая активность"""

    return UserProfile(
        id=2,
        uid="test-uid-female",
        username="testuser_female",
        email="female@example.com",
        gender="female",
        age=25,
        weight=60.0,
        height=165.0,
        kfa=KFALevel.LOW,
        goal=GoalType.LOSE_WEIGHT,
        created_at="2024-01-01T00:00:00",
        is_subscribed=True,
    )


class TestCalculateBMR:
    """Тесты для расчёта базального метаболизма (BMR)"""

    def test_bmr_male_calculation(self, male_user_profile):
        """Тест расчёта BMR для мужчины"""
        # BMR = 10 * 80 + 6.25 * 180 - 5 * 30 + 5 = 1780
        expected_bmr = 1780.0
        result = calculate_bmr(male_user_profile)
        assert result == expected_bmr

    def test_bmr_female_calculation(self, female_user_profile):
        """Тест расчёта BMR для женщины"""
        # BMR = 10 * 60 + 6.25 * 165 - 5 * 25 - 161 = 1345.25
        expected_bmr = 1345.25
        result = calculate_bmr(female_user_profile)
        assert result == expected_bmr

    def test_bmr_missing_gender(self, male_user_profile):
        """Тест с отсутствующим полом"""
        male_user_profile.gender = None
        with pytest.raises(ValueError, match="Missing required fields"):
            calculate_bmr(male_user_profile)

    def test_bmr_missing_age(self, male_user_profile):
        """Тест с отсутствующим возрастом"""
        male_user_profile.age = None
        with pytest.raises(ValueError, match="Missing required fields"):
            calculate_bmr(male_user_profile)

    def test_bmr_missing_weight(self, male_user_profile):
        """Тест с отсутствующим весом"""
        male_user_profile.weight = None
        with pytest.raises(ValueError, match="Missing required fields"):
            calculate_bmr(male_user_profile)

    def test_bmr_missing_height(self, male_user_profile):
        """Тест с отсутствующим ростом"""
        male_user_profile.height = None
        with pytest.raises(ValueError, match="Missing required fields"):
            calculate_bmr(male_user_profile)

    def test_bmr_invalid_age_zero(self, male_user_profile):
        """Тест с нулевым возрастом"""
        male_user_profile.age = 0
        with pytest.raises(ValueError, match="Invalid age"):
            calculate_bmr(male_user_profile)

    def test_bmr_invalid_age_negative(self, male_user_profile):
        """Тест с отрицательным возрастом"""
        male_user_profile.age = -5
        with pytest.raises(ValueError, match="Invalid age"):
            calculate_bmr(male_user_profile)

    def test_bmr_invalid_age_too_high(self, male_user_profile):
        """Тест с возрастом > 120"""
        male_user_profile.age = 150
        with pytest.raises(ValueError, match="Invalid age"):
            calculate_bmr(male_user_profile)

    def test_bmr_invalid_weight_zero(self, male_user_profile):
        """Тест с нулевым весом"""
        male_user_profile.weight = 0
        with pytest.raises(ValueError, match="Invalid weight"):
            calculate_bmr(male_user_profile)

    def test_bmr_invalid_weight_negative(self, male_user_profile):
        """Тест с отрицательным весом"""
        male_user_profile.weight = -10
        with pytest.raises(ValueError, match="Invalid weight"):
            calculate_bmr(male_user_profile)

    def test_bmr_invalid_weight_too_high(self, male_user_profile):
        """Тест с весом > 500 кг"""
        male_user_profile.weight = 600
        with pytest.raises(ValueError, match="Invalid weight"):
            calculate_bmr(male_user_profile)

    def test_bmr_invalid_height_zero(self, male_user_profile):
        """Тест с нулевым ростом"""
        male_user_profile.height = 0
        with pytest.raises(ValueError, match="Invalid height"):
            calculate_bmr(male_user_profile)

    def test_bmr_invalid_height_negative(self, male_user_profile):
        """Тест с отрицательным ростом"""
        male_user_profile.height = -50
        with pytest.raises(ValueError, match="Invalid height"):
            calculate_bmr(male_user_profile)

    def test_bmr_invalid_height_too_high(self, male_user_profile):
        """Тест с ростом > 300 см"""
        male_user_profile.height = 350
        with pytest.raises(ValueError, match="Invalid height"):
            calculate_bmr(male_user_profile)

    def test_bmr_boundary_age_min(self, male_user_profile):
        """Тест с минимальным возрастом (1 год)"""
        male_user_profile.age = 1
        result = calculate_bmr(male_user_profile)
        assert result == 1925.0

    def test_bmr_boundary_age_max(self, male_user_profile):
        """Тест с максимальным возрастом (120 лет)"""
        male_user_profile.age = 120
        result = calculate_bmr(male_user_profile)
        assert result == 1330.0

    @pytest.mark.parametrize(
        "gender,age,weight,height,expected_bmr",
        [
            ("male", 20, 70, 175, 1698.75),
            ("male", 40, 90, 185, 1861.25),
            ("female", 20, 55, 160, 1289.0),
            ("female", 40, 70, 170, 1401.5),
        ],
    )
    def test_bmr_various_combinations(
        self, male_user_profile, gender, age, weight, height, expected_bmr
    ):
        """Тест различных комбинаций параметров"""
        male_user_profile.gender = gender
        male_user_profile.age = age
        male_user_profile.weight = weight
        male_user_profile.height = height
        result = calculate_bmr(male_user_profile)
        assert result == expected_bmr


class TestCalculateTDEE:
    """Тесты для расчёта суточной нормы калорий (TDEE)"""

    def test_tdee_with_kfa_medium(self, male_user_profile):
        """Тест TDEE с средней активностью (KFA=3)"""
        expected_tdee = 1780.0 * 3.0
        result = calculate_tdee(male_user_profile)
        assert result == expected_tdee

    def test_tdee_with_kfa_low(self, female_user_profile):
        """Тест TDEE с низкой активностью (KFA=2)"""
        expected_tdee = 1345.25 * 2.0
        result = calculate_tdee(female_user_profile)
        assert result == expected_tdee

    def test_tdee_with_kfa_very_low(self, male_user_profile):
        """Тест TDEE с очень низкой активностью (KFA=1)"""
        male_user_profile.kfa = KFALevel.VERY_LOW
        expected_tdee = 1780.0 * 1.0
        result = calculate_tdee(male_user_profile)
        assert result == expected_tdee

    def test_tdee_with_kfa_high(self, male_user_profile):
        """Тест TDEE с высокой активностью (KFA=4)"""
        male_user_profile.kfa = KFALevel.HIGH
        expected_tdee = 1780.0 * 4.0
        result = calculate_tdee(male_user_profile)
        assert result == expected_tdee

    def test_tdee_with_kfa_very_high(self, male_user_profile):
        """Тест TDEE с очень высокой активностью (KFA=5)"""
        male_user_profile.kfa = KFALevel.VERY_HIGH
        expected_tdee = 1780.0 * 5.0
        result = calculate_tdee(male_user_profile)
        assert result == expected_tdee

    def test_tdee_missing_kfa(self, male_user_profile):
        """Тест с отсутствующим KFA"""
        male_user_profile.kfa = None
        with pytest.raises(ValueError, match="Activity factor .* is required"):
            calculate_tdee(male_user_profile)

    def test_tdee_propagates_bmr_errors(self, male_user_profile):
        """Тест что TDEE пробрасывает ошибки BMR"""
        male_user_profile.age = None
        with pytest.raises(ValueError, match="Missing required fields"):
            calculate_tdee(male_user_profile)

    @pytest.mark.parametrize(
        "kfa_level,expected_multiplier",
        [
            (KFALevel.VERY_LOW, 1.0),
            (KFALevel.LOW, 2.0),
            (KFALevel.MEDIUM, 3.0),
            (KFALevel.HIGH, 4.0),
            (KFALevel.VERY_HIGH, 5.0),
        ],
    )
    def test_tdee_all_kfa_levels(
        self, male_user_profile, kfa_level, expected_multiplier
    ):
        """Тест всех уровней KFA"""
        male_user_profile.kfa = kfa_level
        bmr = calculate_bmr(male_user_profile)
        expected_tdee = bmr * expected_multiplier
        result = calculate_tdee(male_user_profile)
        assert result == expected_tdee

    def test_tdee_consistency_with_bmr(self, male_user_profile):
        """Тест что TDEE всегда >= BMR (при KFA >= 1)"""
        bmr = calculate_bmr(male_user_profile)
        tdee = calculate_tdee(male_user_profile)
        assert tdee >= bmr
