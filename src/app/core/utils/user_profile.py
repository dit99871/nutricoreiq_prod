from src.app.core.logger import get_logger
from src.app.core.models.user import KFALevel
from src.app.core.schemas import UserProfile

log = get_logger("user_utils")


def calculate_bmr(user: UserProfile) -> float:
    """
    Calculates the Basal Metabolic Rate (BMR) of the given user.

    The BMR is the number of calories the body needs to function at rest. It is
    calculated using the following formulas:
    - For men: BMR = 10 * weight (kg) + 6.25 * height (cm) - 5 * age (y) + 5
    - For women: BMR = 10 * weight (kg) + 6.25 * height (cm) - 5 * age (y) - 161

    :param user: A UserAccount object with required fields (gender, age, weight, height).
    :return: The calculated BMR as a float.
    :raises ValueError: If required fields are missing or invalid (e.g., negative values).
    """

    # проверка на наличие всех необходимых полей
    required_fields = ["gender", "age", "weight", "height"]
    missing_fields = [
        field for field in required_fields if getattr(user, field) is None
    ]
    if missing_fields:
        log.error(
            "Не заполнены поля: %s",
            missing_fields,
        )
        raise ValueError(
            f"Missing required fields for BMR calculation: {missing_fields}"
        )

    # извлечение данных
    gender = user.gender
    age = user.age
    weight = user.weight
    height = user.height

    # валидация значений
    if age <= 0 or age > 120:
        raise ValueError(f"Invalid age: {age}. Must be between 1 and 120.")
    if weight <= 0 or weight > 500:
        raise ValueError(f"Invalid weight: {weight}. Must be between 0 and 500 kg.")
    if height <= 0 or height > 300:
        raise ValueError(f"Invalid height: {height}. Must be between 0 and 300 cm.")

    # расчёт BMR
    bmr = 10 * weight + 6.25 * height - 5 * age
    if gender == "male":
        bmr += 5
    else:  # gender == "female"
        bmr -= 161

    log.debug(
        f"Calculated BMR for user (gender={gender}, age={age}, weight={weight}, height={height}): {bmr}"
    )
    return bmr


def calculate_tdee(user: UserProfile) -> float:
    """
    Calculates the Total Daily Energy Expenditure (TDEE) of the given user.

    The TDEE is the total number of calories the body needs daily to function. It
    is calculated by multiplying the Basal Metabolic Rate (BMR) by the user's
    activity level factor (kfa).

    :param user: A UserAccount object with required fields (gender, age, weight, height, kfa).
    :return: The calculated TDEE as a float.
    :raises ValueError: If required fields are missing or invalid (e.g., kfa is not a valid number).
    """

    # проверка kfa
    if user.kfa is None:
        log.error("Отсутствует kfa для пользователя: %s", user)
        raise ValueError("Activity factor (kfa) is required for TDEE calculation.")

    try:
        if isinstance(user.kfa, KFALevel):
            kfa = float(user.kfa.value)  # "1".."5" -> 1.0..5.0
        else:
            kfa = float(user.kfa)  # fallback на случай исторических значений
    except Exception as e:
        log.error("Ошибка значения kfa: %s", str(e))
        raise ValueError(
            f"Invalid kfa: {user.kfa}. Must be an enum or a string/number representing a number (e.g., '1')."
        )

    if kfa < 1.0 or kfa > 5.0:
        log.error("Ошибка валидации kfa")
        raise ValueError(f"Invalid kfa: {kfa}. Must be between 1.0 and 5.0.")

    bmr = calculate_bmr(user)
    tdee = bmr * kfa
    log.debug(f"Calculated TDEE for user (bmr={bmr}, kfa={kfa}): {tdee}")

    return tdee
