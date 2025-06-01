import pytest
from pydantic import ValidationError  # Добавлен импорт
from src.app.schemas.user import UserAccount

from src.app.services.user import calculate_bmr, calculate_tdee


# Фикстура для создания тестового пользователя (мужчина)
@pytest.fixture
def user_male():
    return UserAccount(
        username="testuser_male",
        email="testmale@example.com",
        gender="male",
        age=30,
        weight=70.0,
        height=175.0,
        kfa="1.5",
        goal="Поддержание веса",
        created_at="2025-06-01T16:00:00Z",
    )


# Фикстура для создания тестового пользователя (женщина)
@pytest.fixture
def user_female():
    return UserAccount(
        username="testuser_female",
        email="testfemale@example.com",
        gender="female",
        age=25,
        weight=60.0,
        height=165.0,
        kfa="1.4",
        goal="Снижение веса",
        created_at="2025-06-01T16:00:00Z",
    )


# Тесты для calculate_bmr
def test_calculate_bmr_male(user_male):
    """Проверяет расчёт BMR для мужчины."""
    # Ожидаемое значение: 10 * 70 + 6.25 * 175 - 5 * 30 + 5 = 700 + 1093.75 - 150 + 5 = 1648.75
    assert calculate_bmr(user_male) == pytest.approx(1648.75, rel=1e-9)


def test_calculate_bmr_female(user_female):
    """Проверяет расчёт BMR для женщины."""
    # Ожидаемое значение: 10 * 60 + 6.25 * 165 - 5 * 25 - 161 = 600 + 1031.25 - 125 - 161 = 1345.25
    assert calculate_bmr(user_female) == pytest.approx(1345.25, rel=1e-9)


def test_calculate_bmr_invalid_gender():
    """Проверяет поведение при некорректном gender."""
    with pytest.raises(
        ValidationError,  # Используем pydantic.ValidationError вместо pydantic_core._pydantic_core.ValidationError
        match="Input should be 'female' or 'male'",
    ):
        UserAccount(
            username="testuser_invalid",
            email="testinvalid@example.com",
            gender="other",
            age=30,
            weight=70.0,
            height=175.0,
            kfa="1.5",
            goal="Поддержание веса",
            created_at="2025-06-01T16:00:00Z",
        )


def test_calculate_bmr_none_gender():
    """Проверяет поведение при отсутствии gender."""
    user = UserAccount(
        username="testuser_none",
        email="testnone@example.com",
        gender=None,
        age=30,
        weight=70.0,
        height=175.0,
        kfa="1.5",
        goal="Поддержание веса",
        created_at="2025-06-01T16:00:00Z",
    )
    with pytest.raises(
        ValueError, match="Missing required fields for BMR calculation: \\['gender'\\]"
    ):
        calculate_bmr(user)


def test_calculate_bmr_none_age():
    """Проверяет поведение при отсутствии age."""
    user = UserAccount(
        username="testuser_none",
        email="testnone@example.com",
        gender="male",
        age=None,
        weight=70.0,
        height=175.0,
        kfa="1.5",
        goal="Поддержание веса",
        created_at="2025-06-01T16:00:00Z",
    )
    with pytest.raises(
        ValueError, match="Missing required fields for BMR calculation: \\['age'\\]"
    ):
        calculate_bmr(user)


def test_calculate_bmr_none_weight():
    """Проверяет поведение при отсутствии weight."""
    user = UserAccount(
        username="testuser_none",
        email="testnone@example.com",
        gender="male",
        age=30,
        weight=None,
        height=175.0,
        kfa="1.5",
        goal="Поддержание веса",
        created_at="2025-06-01T16:00:00Z",
    )
    with pytest.raises(
        ValueError, match="Missing required fields for BMR calculation: \\['weight'\\]"
    ):
        calculate_bmr(user)


def test_calculate_bmr_none_height():
    """Проверяет поведение при отсутствии height."""
    user = UserAccount(
        username="testuser_none",
        email="testnone@example.com",
        gender="male",
        age=30,
        weight=70.0,
        height=None,
        kfa="1.5",
        goal="Поддержание веса",
        created_at="2025-06-01T16:00:00Z",
    )
    with pytest.raises(
        ValueError, match="Missing required fields for BMR calculation: \\['height'\\]"
    ):
        calculate_bmr(user)


def test_calculate_bmr_invalid_age():
    """Проверяет поведение при некорректном возрасте (отрицательное значение)."""
    user = UserAccount(
        username="testuser_invalid",
        email="testinvalid@example.com",
        gender="male",
        age=-1,
        weight=70.0,
        height=175.0,
        kfa="1.5",
        goal="Поддержание веса",
        created_at="2025-06-01T16:00:00Z",
    )
    with pytest.raises(ValueError, match="Invalid age: -1. Must be between 1 and 120."):
        calculate_bmr(user)


def test_calculate_bmr_invalid_weight():
    """Проверяет поведение при некорректном весе (отрицательное значение)."""
    user = UserAccount(
        username="testuser_invalid",
        email="testinvalid@example.com",
        gender="male",
        age=30,
        weight=-10.0,
        height=175.0,
        kfa="1.5",
        goal="Поддержание веса",
        created_at="2025-06-01T16:00:00Z",
    )
    with pytest.raises(
        ValueError, match="Invalid weight: -10.0. Must be between 0 and 500 kg."
    ):
        calculate_bmr(user)


def test_calculate_bmr_invalid_height():
    """Проверяет поведение при некорректной высоте (отрицательное значение)."""
    user = UserAccount(
        username="testuser_invalid",
        email="testinvalid@example.com",
        gender="male",
        age=30,
        weight=70.0,
        height=-175.0,
        kfa="1.5",
        goal="Поддержание веса",
        created_at="2025-06-01T16:00:00Z",
    )
    with pytest.raises(
        ValueError, match="Invalid height: -175.0. Must be between 0 and 300 cm."
    ):
        calculate_bmr(user)


# Тесты для calculate_tdee
def test_calculate_tdee_male(user_male):
    """Проверяет расчёт TDEE для мужчины."""
    bmr = 1648.75  # Из предыдущего теста
    expected_tdee = bmr * 1.5  # kfa = "1.5"
    assert calculate_tdee(user_male) == pytest.approx(expected_tdee, rel=1e-9)


def test_calculate_tdee_female(user_female):
    """Проверяет расчёт TDEE для женщины."""
    bmr = 1345.25  # Из предыдущего теста
    expected_tdee = bmr * 1.4  # kfa = "1.4"
    assert calculate_tdee(user_female) == pytest.approx(expected_tdee, rel=1e-9)


def test_calculate_tdee_none_kfa():
    """Проверяет поведение при отсутствии kfa."""
    user = UserAccount(
        username="testuser_none",
        email="testnone@example.com",
        gender="male",
        age=30,
        weight=70.0,
        height=175.0,
        kfa=None,
        goal="Поддержание веса",
        created_at="2025-06-01T16:00:00Z",
    )
    with pytest.raises(
        ValueError, match="Activity factor \\(kfa\\) is required for TDEE calculation."
    ):
        calculate_tdee(user)


def test_calculate_tdee_invalid_kfa():
    """Проверяет поведение при некорректном kfa (не число)."""
    user = UserAccount(
        username="testuser_invalid",
        email="testinvalid@example.com",
        gender="male",
        age=30,
        weight=70.0,
        height=175.0,
        kfa="invalid",
        goal="Поддержание веса",
        created_at="2025-06-01T16:00:00Z",
    )
    with pytest.raises(
        ValueError,
        match="Invalid kfa: invalid. Must be a string representing a number \\(e.g., '1.5'\\).",
    ):
        calculate_tdee(user)


def test_calculate_tdee_out_of_range_kfa():
    """Проверяет поведение при kfa вне допустимого диапазона."""
    user = UserAccount(
        username="testuser_invalid",
        email="testinvalid@example.com",
        gender="male",
        age=30,
        weight=70.0,
        height=175.0,
        kfa="3.0",
        goal="Поддержание веса",
        created_at="2025-06-01T16:00:00Z",
    )
    with pytest.raises(
        ValueError, match="Invalid kfa: 3.0. Must be between 1.0 and 2.5."
    ):
        calculate_tdee(user)


def test_calculate_tdee_boundary_kfa():
    """Проверяет расчёт TDEE с граничным значением kfa."""
    user = UserAccount(
        username="testuser_boundary",
        email="testboundary@example.com",
        gender="male",
        age=30,
        weight=70.0,
        height=175.0,
        kfa="1.0",
        goal="Поддержание веса",
        created_at="2025-06-01T16:00:00Z",
    )
    bmr = 1648.75  # Из предыдущего теста
    expected_tdee = bmr * 1.0
    assert calculate_tdee(user) == pytest.approx(expected_tdee, rel=1e-9)


def test_calculate_tdee_logging(caplog, user_male):
    """Проверяет, что логи записываются при расчёте TDEE."""
    caplog.set_level("DEBUG")
    bmr = 1648.75
    kfa = 1.5
    expected_tdee = bmr * kfa

    result = calculate_tdee(user_male)

    assert result == pytest.approx(expected_tdee, rel=1e-9)
    assert (
        f"Calculated BMR for user (gender=male, age=30, weight=70.0, height=175.0): {bmr}"
        in caplog.text
    )
    assert (
        f"Calculated TDEE for user (bmr={bmr}, kfa={kfa}): {expected_tdee}"
        in caplog.text
    )
