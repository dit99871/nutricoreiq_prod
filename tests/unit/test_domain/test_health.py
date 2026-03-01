"""
Тесты для доменной логики расчёта BMR и TDEE.
"""

import pytest

from src.app.core.domain.health import HealthCalculator
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
        result = HealthCalculator.calculate_bmr(male_user_profile)
        assert result == expected_bmr

    def test_bmr_female_calculation(self, female_user_profile):
        """Тест расчёта BMR для женщины"""
        # BMR = 10 * 60 + 6.25 * 165 - 5 * 25 - 161 = 1345.25
        expected_bmr = 1345.25
        result = HealthCalculator.calculate_bmr(female_user_profile)
        assert result == expected_bmr

    def test_bmr_missing_gender(self, male_user_profile):
        """Тест с отсутствующим полом"""
        male_user_profile.gender = None
        with pytest.raises(
            ValueError, match="Отсутствуют обязательные поля для расчёта BMR"
        ):
            HealthCalculator.calculate_bmr(male_user_profile)

    def test_bmr_missing_age(self, male_user_profile):
        """Тест с отсутствующим возрастом"""
        male_user_profile.age = None
        with pytest.raises(
            ValueError, match="Отсутствуют обязательные поля для расчёта BMR"
        ):
            HealthCalculator.calculate_bmr(male_user_profile)

    def test_bmr_missing_weight(self, male_user_profile):
        """Тест с отсутствующим весом"""
        male_user_profile.weight = None
        with pytest.raises(
            ValueError, match="Отсутствуют обязательные поля для расчёта BMR: weight"
        ):
            HealthCalculator.calculate_bmr(male_user_profile)

    def test_bmr_missing_height(self, male_user_profile):
        """Тест с отсутствующим ростом"""
        male_user_profile.height = None
        with pytest.raises(
            ValueError, match="Отсутствуют обязательные поля для расчёта BMR: height"
        ):
            HealthCalculator.calculate_bmr(male_user_profile)

    def test_bmr_invalid_age_zero(self, male_user_profile):
        """Тест с нулевым возрастом"""
        male_user_profile.age = 0
        with pytest.raises(
            ValueError, match="Недопустимый возраст: 0. Должен быть от 1 до 120 лет."
        ):
            HealthCalculator.calculate_bmr(male_user_profile)

    def test_bmr_invalid_age_negative(self, male_user_profile):
        """Тест с отрицательным возрастом"""
        male_user_profile.age = -5
        with pytest.raises(
            ValueError, match="Недопустимый возраст: -5. Должен быть от 1 до 120 лет."
        ):
            HealthCalculator.calculate_bmr(male_user_profile)

    def test_bmr_invalid_age_too_high(self, male_user_profile):
        """Тест с возрастом > 120"""
        male_user_profile.age = 150
        with pytest.raises(
            ValueError, match="Недопустимый возраст: 150. Должен быть от 1 до 120 лет."
        ):
            HealthCalculator.calculate_bmr(male_user_profile)

    def test_bmr_invalid_weight_zero(self, male_user_profile):
        """Тест с нулевым весом"""
        male_user_profile.weight = 0
        with pytest.raises(
            ValueError, match="Недопустимый вес: 0. Должен быть от 0.1 до 500 кг."
        ):
            HealthCalculator.calculate_bmr(male_user_profile)

    def test_bmr_invalid_weight_negative(self, male_user_profile):
        """Тест с отрицательным весом"""
        male_user_profile.weight = -10
        with pytest.raises(
            ValueError, match="Недопустимый вес: -10. Должен быть от 0.1 до 500 кг."
        ):
            HealthCalculator.calculate_bmr(male_user_profile)

    def test_bmr_invalid_weight_too_high(self, male_user_profile):
        """Тест с весом > 500 кг"""
        male_user_profile.weight = 600
        with pytest.raises(
            ValueError, match="Недопустимый вес: 600. Должен быть от 0.1 до 500 кг."
        ):
            HealthCalculator.calculate_bmr(male_user_profile)

    def test_bmr_invalid_height_zero(self, male_user_profile):
        """Тест с нулевым ростом"""
        male_user_profile.height = 0
        with pytest.raises(
            ValueError, match="Недопустимый рост: 0. Должен быть от 1 до 300 см."
        ):
            HealthCalculator.calculate_bmr(male_user_profile)

    def test_bmr_invalid_height_negative(self, male_user_profile):
        """Тест с отрицательным ростом"""
        male_user_profile.height = -50
        with pytest.raises(
            ValueError, match="Недопустимый рост: -50. Должен быть от 1 до 300 см."
        ):
            HealthCalculator.calculate_bmr(male_user_profile)

    def test_bmr_invalid_height_too_high(self, male_user_profile):
        """Тест с ростом > 300 см"""
        male_user_profile.height = 350
        with pytest.raises(
            ValueError, match="Недопустимый рост: 350. Должен быть от 1 до 300 см."
        ):
            HealthCalculator.calculate_bmr(male_user_profile)

    def test_bmr_boundary_age_min(self, male_user_profile):
        """Тест с минимальным возрастом (1 год)"""
        male_user_profile.age = 1
        result = HealthCalculator.calculate_bmr(male_user_profile)
        assert result == 1925.0

    def test_bmr_boundary_age_max(self, male_user_profile):
        """Тест с максимальным возрастом (120 лет)"""
        male_user_profile.age = 120
        result = HealthCalculator.calculate_bmr(male_user_profile)
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
        result = HealthCalculator.calculate_bmr(male_user_profile)
        assert result == expected_bmr


class TestCalculateTDEE:
    """Тесты для расчёта суточной нормы калорий (TDEE)"""

    def test_tdee_with_kfa_medium(self, male_user_profile):
        """Тест TDEE с средней активностью (KFA=1.55)"""
        expected_tdee = 1780.0 * 1.55
        result = HealthCalculator.calculate_tdee(male_user_profile)
        assert result == expected_tdee

    def test_tdee_with_kfa_low(self, female_user_profile):
        """Тест TDEE с низкой активностью (KFA=1.375)"""
        expected_tdee = 1345.25 * 1.375
        result = HealthCalculator.calculate_tdee(female_user_profile)
        assert result == expected_tdee

    def test_tdee_with_kfa_very_low(self, male_user_profile):
        """Тест TDEE с очень низкой активностью (KFA=1.2)"""
        male_user_profile.kfa = KFALevel.VERY_LOW
        expected_tdee = 1780.0 * 1.2
        result = HealthCalculator.calculate_tdee(male_user_profile)
        assert result == expected_tdee

    def test_tdee_with_kfa_high(self, male_user_profile):
        """Тест TDEE с высокой активностью (KFA=1.725)"""
        male_user_profile.kfa = KFALevel.HIGH
        expected_tdee = 1780.0 * 1.725
        result = HealthCalculator.calculate_tdee(male_user_profile)
        assert result == expected_tdee

    def test_tdee_with_kfa_very_high(self, male_user_profile):
        """Тест TDEE с очень высокой активностью (KFA=1.9)"""
        male_user_profile.kfa = KFALevel.VERY_HIGH
        expected_tdee = 1780.0 * 1.9
        result = HealthCalculator.calculate_tdee(male_user_profile)
        assert result == expected_tdee

    def test_tdee_missing_kfa(self, male_user_profile):
        """Тест с отсутствующим KFA"""
        male_user_profile.kfa = None
        with pytest.raises(
            ValueError, match="Для расчёта TDEE необходим коэффициент активности"
        ):
            HealthCalculator.calculate_tdee(male_user_profile)

    def test_tdee_propagates_bmr_errors(self, male_user_profile):
        """Тест что TDEE пробрасывает ошибки BMR"""
        male_user_profile.age = None
        with pytest.raises(
            ValueError, match="Отсутствуют обязательные поля для расчёта BMR"
        ):
            HealthCalculator.calculate_tdee(male_user_profile)

    @pytest.mark.parametrize(
        "kfa_level,expected_multiplier",
        [
            (KFALevel.VERY_LOW, 1.2),
            (KFALevel.LOW, 1.375),
            (KFALevel.MEDIUM, 1.55),
            (KFALevel.HIGH, 1.725),
            (KFALevel.VERY_HIGH, 1.9),
        ],
    )
    def test_tdee_all_kfa_levels(
        self, male_user_profile, kfa_level, expected_multiplier
    ):
        """Тест всех уровней KFA"""
        male_user_profile.kfa = kfa_level
        bmr = HealthCalculator.calculate_bmr(male_user_profile)
        expected_tdee = bmr * expected_multiplier
        result = HealthCalculator.calculate_tdee(male_user_profile)
        assert result == expected_tdee

    def test_tdee_consistency_with_bmr(self, male_user_profile):
        """Тест что TDEE всегда >= BMR (при KFA >= 1)"""
        bmr = HealthCalculator.calculate_bmr(male_user_profile)
        tdee = HealthCalculator.calculate_tdee(male_user_profile)
        assert tdee >= bmr


class TestCalculateAdjustedTDEE:
    """Тесты для расчёта скорректированного TDEE"""

    def test_adjusted_tdee_maintain_weight(self, male_user_profile):
        """Тест скорректированного TDEE для поддержания веса (без изменений)"""
        base_tdee = 1780.0 * 1.55  # 2759 ккал
        result = HealthCalculator.calculate_adjusted_tdee(male_user_profile)
        assert result == base_tdee

    def test_adjusted_tdee_gain_weight(self, male_user_profile):
        """Тест скорректированного TDEE для набора веса (+400 ккал)"""
        male_user_profile.goal = GoalType.GAIN_WEIGHT
        base_tdee = 1780.0 * 1.55  # 2759 ккал
        expected = base_tdee + 400  # 3159 ккал
        result = HealthCalculator.calculate_adjusted_tdee(male_user_profile)
        assert result == expected

    def test_adjusted_tdee_lose_weight(self, male_user_profile):
        """Тест скорректированного TDEE для снижения веса (-500 ккал)"""
        male_user_profile.goal = GoalType.LOSE_WEIGHT
        base_tdee = 1780.0 * 1.55  # 2759 ккал
        expected = base_tdee - 500  # 2259 ккал
        result = HealthCalculator.calculate_adjusted_tdee(male_user_profile)
        assert result == expected

    def test_adjusted_tdee_missing_goal(self, male_user_profile):
        """Тест с отсутствующей целью"""
        male_user_profile.goal = None
        with pytest.raises(
            ValueError, match="Для расчета скорректированного TDEE необходимо указать цель"
        ):
            HealthCalculator.calculate_adjusted_tdee(male_user_profile)

    def test_adjusted_tdee_propagates_tdee_errors(self, male_user_profile):
        """Тест на то, что скорректированный TDEE пробрасывает ошибки TDEE"""
        male_user_profile.age = None
        with pytest.raises(
            ValueError, match="Отсутствуют обязательные поля для расчёта BMR"
        ):
            HealthCalculator.calculate_adjusted_tdee(male_user_profile)


class TestCalculateNutrients:
    """Тесты для расчёта нутриентов"""

    def test_nutrients_maintain_weight(self, male_user_profile):
        """Тест расчёта нутриентов для поддержания веса"""
        tdee = 1780.0 * 1.9  # 3382 ккал
        expected_carbs = round(3382 * 0.55 / 4)  # 465 г
        expected_protein = round(3382 * 0.20 / 4)  # 169 г
        expected_fat = round(3382 * 0.25 / 9)  # 94 г
        
        result = HealthCalculator.calculate_nutrients(male_user_profile, tdee)
        
        assert result["carbs"] == expected_carbs
        assert result["protein"] == expected_protein
        assert result["fat"] == expected_fat

    def test_nutrients_gain_weight(self, male_user_profile):
        """Тест расчёта нутриентов для набора веса"""
        male_user_profile.goal = GoalType.GAIN_WEIGHT
        tdee = 1780.0 * 1.9  # 3382 ккал
        expected_carbs = round(3382 * 0.55 / 4)  # 465 г
        expected_protein = round(3382 * 0.25 / 4)  # 211 г
        expected_fat = round(3382 * 0.20 / 9)  # 75 г
        
        result = HealthCalculator.calculate_nutrients(male_user_profile, tdee)
        
        assert result["carbs"] == expected_carbs
        assert result["protein"] == expected_protein
        assert result["fat"] == expected_fat

    def test_nutrients_lose_weight(self, female_user_profile):
        """Тест расчёта нутриентов для снижения веса"""
        tdee = 1345.25 * 1.6  # 2152.4 ккал
        expected_carbs = round(2152.4 * 0.45 / 4)  # 242 г
        expected_protein = round(2152.4 * 0.30 / 4)  # 161 г
        expected_fat = round(2152.4 * 0.25 / 9)  # 60 г
        
        result = HealthCalculator.calculate_nutrients(female_user_profile, tdee)
        
        assert result["carbs"] == expected_carbs
        assert result["protein"] == expected_protein
        assert result["fat"] == expected_fat

    def test_nutrients_missing_goal(self, male_user_profile):
        """Тест с отсутствующей целью"""
        male_user_profile.goal = None
        tdee = 2000.0
        
        with pytest.raises(
            ValueError, match="Для расчёта нутриентов необходимо указать цель"
        ):
            HealthCalculator.calculate_nutrients(male_user_profile, tdee)

    @pytest.mark.parametrize(
        "tdee,goal,expected_carbs,expected_protein,expected_fat",
        [
            # TDEE=2000, поддержание веса: 55% carbs, 20% protein, 25% fat
            (2000.0, GoalType.MAINTAIN_WEIGHT, 275, 100, 56),
            # TDEE=2000, набор веса: 55% carbs, 25% protein, 20% fat  
            (2000.0, GoalType.GAIN_WEIGHT, 275, 125, 44),
            # TDEE=2000, снижение веса: 45% carbs, 30% protein, 25% fat
            (2000.0, GoalType.LOSE_WEIGHT, 225, 150, 56),
        ],
    )
    def test_nutrients_different_goals_and_tdee(
        self, male_user_profile, tdee, goal, expected_carbs, expected_protein, expected_fat
    ):
        """Тест различных целей и значений TDEE"""
        male_user_profile.goal = goal
        result = HealthCalculator.calculate_nutrients(male_user_profile, tdee)
        
        assert result["carbs"] == expected_carbs
        assert result["protein"] == expected_protein
        assert result["fat"] == expected_fat

    def test_nutrients_rounding_up(self, male_user_profile):
        """Тест правильного округления"""
        male_user_profile.goal = GoalType.MAINTAIN_WEIGHT
        tdee = 1999.0  # Нечетное число для проверки округления
        
        result = HealthCalculator.calculate_nutrients(male_user_profile, tdee)
        
        # Проверяем, что значения округлены правильно
        carbs_calories = tdee * 0.55  # 1099.45
        expected_carbs = round(carbs_calories / 4)  # 275
        assert result["carbs"] == expected_carbs


class TestUserServiceNutrients:
    """Тесты для метода расчета нутриентов в UserService"""

    def test_calculate_user_nutrients_complete_profile(self, male_user_profile):
        """Тест расчета нутриентов для полностью заполненного профиля"""
        from src.app.core.services.user_service import UserService
        from unittest.mock import Mock
        
        # Создаем мок-сессии
        mock_session = Mock()
        user_service = UserService(mock_session)
        
        result = user_service.calculate_user_nutrients(male_user_profile)
        
        assert result is not None
        assert "tdee" in result
        assert "nutrients" in result
        assert result["tdee"] > 0
        assert "carbs" in result["nutrients"]
        assert "protein" in result["nutrients"]
        assert "fat" in result["nutrients"]
        assert result["nutrients"]["carbs"] > 0
        assert result["nutrients"]["protein"] > 0
        assert result["nutrients"]["fat"] > 0

    def test_calculate_user_nutrients_gain_weight_adjustment(self, male_user_profile):
        """Тест на то, что для набора веса TDEE увеличивается на 400"""
        from src.app.core.services.user_service import UserService
        from unittest.mock import Mock
        
        # Устанавливаем цель набор веса
        male_user_profile.goal = GoalType.GAIN_WEIGHT
        
        mock_session = Mock()
        user_service = UserService(mock_session)
        
        result = user_service.calculate_user_nutrients(male_user_profile)
        
        assert result is not None
        base_tdee = 1780.0 * 1.55  # 2759 ккал
        expected_tdee = base_tdee + 400  # 3159 ккал
        assert result["tdee"] == expected_tdee

    def test_calculate_user_nutrients_incomplete_profile(self, male_user_profile):
        """Тест расчета нутриентов для неполного профиля"""
        from src.app.core.services.user_service import UserService
        from unittest.mock import Mock
        
        # Убираем цель
        male_user_profile.goal = None
        
        mock_session = Mock()
        user_service = UserService(mock_session)
        
        result = user_service.calculate_user_nutrients(male_user_profile)
        
        assert result is None

    def test_calculate_user_nutrients_missing_age(self, male_user_profile):
        """Тест расчета нутриентов при отсутствии возраста"""
        from src.app.core.services.user_service import UserService
        from unittest.mock import Mock
        
        # Убираем возраст
        male_user_profile.age = None
        
        mock_session = Mock()
        user_service = UserService(mock_session)
        
        result = user_service.calculate_user_nutrients(male_user_profile)
        
        assert result is None
