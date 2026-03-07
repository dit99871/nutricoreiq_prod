"""
Модуль для расчёта показателей здоровья и метаболизма.
"""

from src.app.core.logger import get_logger
from src.app.core.models.user import KFALevel
from src.app.core.schemas.user import UserProfile

log = get_logger("health_calculator")


class HealthCalculator:
    """
    Класс для расчёта различных показателей здоровья и метаболизма.
    """

    @staticmethod
    def calculate_bmr(user: UserProfile) -> float:
        """
        Рассчитывает базовый уровень метаболизма (BMR) для пользователя.

        BMR - это количество калорий, необходимое организму для поддержания
        основных функций в состоянии покоя.

        Формулы расчёта:
        - Для мужчин: BMR = 10 * вес (кг) + 6.25 * рост (см) - 5 * возраст (лет) + 5
        - Для женщин: BMR = 10 * вес (кг) + 6.25 * рост (см) - 5 * возраст (лет) - 161

        :param user: Объект UserProfile с данными пользователя.
        :return: Рассчитанный BMR (float).
        :raises ValueError: Если отсутствуют обязательные поля или их значения недопустимы.
        """
        # проверка на наличие всех необходимых полей
        required_fields = ["gender", "age", "weight", "height"]
        missing_fields = [
            field for field in required_fields if getattr(user, field) is None
        ]
        if missing_fields:
            log.error(
                "Не заполнены обязательные поля: %s",
                ", ".join(missing_fields),
            )
            raise ValueError(
                f"Отсутствуют обязательные поля для расчёта BMR: {', '.join(missing_fields)}"
            )

        # извлечение данных
        gender = user.gender
        age = user.age
        weight = user.weight
        height = user.height

        # валидация значений
        if age <= 0 or age > 120:
            raise ValueError(
                f"Недопустимый возраст: {age}. Должен быть от 1 до 120 лет."
            )
        if weight <= 0 or weight > 500:
            raise ValueError(
                f"Недопустимый вес: {weight}. Должен быть от 0.1 до 500 кг."
            )
        if height <= 0 or height > 300:
            raise ValueError(
                f"Недопустимый рост: {height}. Должен быть от 1 до 300 см."
            )

        # расчёт BMR
        bmr = 10 * weight + 6.25 * height - 5 * age
        if gender == "male":
            bmr += 5
        else:  # gender == "female"
            bmr -= 161

        return bmr

    @classmethod
    def calculate_tdee(cls, user: UserProfile) -> float:
        """
        Рассчитывает общий дневной расход энергии (TDEE) пользователя.

        TDEE - это общее количество калорий, которое человек тратит за день,
        включая базовый метаболизм и физическую активность.

        :param user: Объект UserProfile с данными пользователя.
        :return: Рассчитанный TDEE (float).
        :raises ValueError: Если отсутствует или недопустим коэффициент активности (kfa).
        """
        # проверка kfa
        if user.kfa is None:
            log.error(
                "Отсутствует коэффициент активности (kfa) для пользователя: %s", user
            )
            raise ValueError("Для расчёта TDEE необходим коэффициент активности (kfa).")

        try:
            if isinstance(user.kfa, KFALevel):
                kfa = float(user.kfa.value)  # "1.2".."1.9" -> 1.2..1.9
            else:
                kfa = float(user.kfa)  # fallback для исторических значений
        except Exception as e:
            log.error("Ошибка значения kfa: %s", str(e))
            raise ValueError(
                f"Недопустимое значение kfa: {user.kfa}. "
                "Должно быть число от 1.2 до 1.9."
            )

        if kfa < 1.2 or kfa > 1.9:
            log.error("Недопустимое значение kfa: %s", kfa)
            raise ValueError(
                f"Недопустимый коэффициент активности (kfa): {kfa}. "
                "Должен быть от 1.2 до 1.9."
            )

        bmr = cls.calculate_bmr(user)
        tdee = bmr * kfa

        return tdee

    @staticmethod
    def calculate_adjusted_tdee(user: UserProfile) -> float:
        """
        Рассчитывает скорректированный TDEE в зависимости от цели пользователя.

        :param user: Объект UserProfile с данными пользователя.
        :return: Скорректированный TDEE (float).
        :raises ValueError: Если отсутствуют необходимые данные или цель не указана.
        """
        base_tdee = HealthCalculator.calculate_tdee(user)

        if not user.goal:
            raise ValueError(
                "Для расчета скорректированного TDEE необходимо указать цель."
            )

        # получаем строковое значение цели
        goal_value = user.goal.value if hasattr(user.goal, "value") else str(user.goal)

        # корректировка tdee в зависимости от цели
        if goal_value == "Увеличение веса":
            return base_tdee + 400
        elif goal_value == "Снижение веса":
            return base_tdee - 500
        elif goal_value == "Поддержание веса":
            return base_tdee
        else:
            raise ValueError(f"Неизвестная цель: {goal_value}")

    @staticmethod
    def calculate_nutrients(user: UserProfile, tdee: float) -> dict:
        """
        Рассчитывает количество нутриентов (углеводов, белков, жиров) на основе цели пользователя.

        :param user: Объект UserProfile с данными пользователя.
        :param tdee: Рассчитанный TDEE (общий дневной расход энергии).
        :return: Словарь с рассчитанными значениями нутриентов в граммах.
        """

        if not user.goal:
            raise ValueError("Для расчёта нутриентов необходимо указать цель.")

        # процентное соотношение нутриентов в зависимости от цели
        goal_ratios = {
            "Поддержание веса": {"carbs": 0.55, "protein": 0.20, "fat": 0.25},
            "Увеличение веса": {"carbs": 0.55, "protein": 0.25, "fat": 0.20},
            "Снижение веса": {"carbs": 0.45, "protein": 0.30, "fat": 0.25},
        }

        # получаем строковое значение цели
        goal_value = user.goal.value if hasattr(user.goal, "value") else str(user.goal)
        ratios = goal_ratios[goal_value]

        # расчет калорийности по нутриентам
        carbs_calories = tdee * ratios["carbs"]
        protein_calories = tdee * ratios["protein"]
        fat_calories = tdee * ratios["fat"]

        # перевод в граммы (углеводы и белки - 4 ккал/г, жиры - 9 ккал/г)
        carbs_grams = round(carbs_calories / 4)
        protein_grams = round(protein_calories / 4)
        fat_grams = round(fat_calories / 9)

        return {"carbs": carbs_grams, "protein": protein_grams, "fat": fat_grams}
