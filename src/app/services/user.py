from schemas.user import UserAccount


def calculate_bmr(user: UserAccount) -> float:
    """
    Calculates the Basal Metabolic Rate (BMR) of the given user.

    The BMR is the number of calories the body needs to function at rest. It is
    calculated using the following formulas:

    For men: BMR = 10 * weight (kg) + 6.25 * height (cm) - 5 * age (y) + 5
    For women: BMR = 10 * weight (kg) + 6.25 * height (cm) - 5 * age (y) - 161

    :param user: A User object
    :return: The calculated BMR
    """
    if user.gender == "male":
        return 10 * user.weight + 6.25 * user.height - 5 * user.age + 5
    return 10 * user.weight + 6.25 * user.height - 5 * user.age - 161


def calculate_tdee(user: UserAccount) -> float:
    """
    Calculates the Total Daily Energy Expenditure (TDEE) of the given user.

    The TDEE is the total number of calories the body needs daily to function. It
    is calculated by multiplying the Basal Metabolic Rate (BMR) by the user's
    activity level factor.

    :param user: A User object
    :return: The calculated TDEE
    """
    return calculate_bmr(user) * int(user.kfa)
