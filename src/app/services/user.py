from src.app.schemas.user import UserAccount
from src.app.core.logger import get_logger

log = get_logger("user_service")


def calculate_bmr(user: UserAccount) -> float:
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
    # Проверка на наличие всех необходимых полей
    required_fields = ["gender", "age", "weight", "height"]
    missing_fields = [
        field for field in required_fields if getattr(user, field) is None
    ]
    if missing_fields:
        raise ValueError(
            f"Missing required fields for BMR calculation: {missing_fields}"
        )

    # Извлечение данных
    gender = user.gender
    age = user.age
    weight = user.weight
    height = user.height

    # Валидация значений
    if age <= 0 or age > 120:
        raise ValueError(f"Invalid age: {age}. Must be between 1 and 120.")
    if weight <= 0 or weight > 500:
        raise ValueError(f"Invalid weight: {weight}. Must be between 0 and 500 kg.")
    if height <= 0 or height > 300:
        raise ValueError(f"Invalid height: {height}. Must be between 0 and 300 cm.")

    # Расчёт BMR
    bmr = 10 * weight + 6.25 * height - 5 * age
    if gender == "male":
        bmr += 5
    else:  # gender == "female"
        bmr -= 161

    log.debug(
        f"Calculated BMR for user (gender={gender}, age={age}, weight={weight}, height={height}): {bmr}"
    )
    return bmr


def calculate_tdee(user: UserAccount) -> float:
    """
    Calculates the Total Daily Energy Expenditure (TDEE) of the given user.

    The TDEE is the total number of calories the body needs daily to function. It
    is calculated by multiplying the Basal Metabolic Rate (BMR) by the user's
    activity level factor (kfa).

    :param user: A UserAccount object with required fields (gender, age, weight, height, kfa).
    :return: The calculated TDEE as a float.
    :raises ValueError: If required fields are missing or invalid (e.g., kfa is not a valid number).
    """
    # Проверка kfa
    if user.kfa is None:
        raise ValueError("Activity factor (kfa) is required for TDEE calculation.")

    try:
        kfa = float(
            user.kfa
        )  # Используем float вместо int для поддержки дробных значений
    except ValueError:
        raise ValueError(
            f"Invalid kfa: {user.kfa}. Must be a string representing a number (e.g., '1.5')."
        )

    # Валидация kfa
    if kfa < 1.0 or kfa > 2.5:
        raise ValueError(f"Invalid kfa: {kfa}. Must be between 1.0 and 2.5.")

    # Вычисление BMR
    bmr = calculate_bmr(user)

    # Вычисление TDEE
    tdee = bmr * kfa
    log.debug(f"Calculated TDEE for user (bmr={bmr}, kfa={kfa}): {tdee}")
    return tdee
