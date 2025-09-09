import pytest
from datetime import datetime
from pydantic import ValidationError, SecretStr
from enum import Enum


# Мокаем валидатор пароля
def mock_validate_password_strength(v: str | SecretStr) -> str:
    """
    Проверяет сложность пароля: наличие строчных и прописных букв, цифр и спецсимволов.
    Возвращает пароль без изменений, если проверка пройдена, иначе поднимает ValueError.
    """

    # Extract the actual string from SecretStr if that's what we got
    password = v.get_secret_value() if isinstance(v, SecretStr) else v

    has_lower = any(c.islower() for c in password)
    has_upper = any(c.isupper() for c in password)
    has_digit = any(c.isdigit() for c in password)
    has_special = any(not c.isalnum() for c in password)

    if not (has_lower and has_upper and has_digit and has_special):
        raise ValueError(
            "Пароль должен содержать строчные и прописные буквы, цифры и спецсимволы"
        )
    return v  # Return the original value to preserve SecretStr if that's what we got


def mock_coerce_kfa(v):
    """Mock function for coerce_kfa validator"""
    if isinstance(v, str):
        v = v.lower()
        if v in {"low", "moderate", "high", "very_high"}:
            return v
    return v


def mock_coerce_goal(v):
    """Mock function for coerce_goal validator"""
    if isinstance(v, str):
        v = v.lower()
        if v in {"weight_loss", "maintenance", "muscle_gain"}:
            return v
    return v


# 1. Создаем моки для enum'ов
class KFALevel(str, Enum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    VERY_HIGH = "very_high"


class GoalType(str, Enum):
    WEIGHT_LOSS = "weight_loss"
    MAINTENANCE = "maintenance"
    MUSCLE_GAIN = "muscle_gain"


# 2. Подменяем импорты перед загрузкой схем
import sys
from unittest.mock import MagicMock

# Создаем мок-модуль для src.app.models.user
mock_models_user = MagicMock()
mock_models_user.KFALevel = KFALevel
mock_models_user.GoalType = GoalType
sys.modules["src.app.models.user"] = mock_models_user

# Мокаем валидатор пароля
sys.modules["src.app.core.utils.validators"] = MagicMock()
sys.modules["src.app.core.utils.validators"].validate_password_strength = (
    mock_validate_password_strength
)
sys.modules["src.app.core.utils.validators"].coerce_kfa = mock_coerce_kfa
sys.modules["src.app.core.utils.validators"].coerce_goal = mock_coerce_goal

# 3. Теперь импортируем схемы
from src.app.schemas.user import (
    UserBaseIn,
    UserBaseOut,
    UserCreate,
    UserPublic,
    UserProfile,
    UserProfileUpdate,
    PasswordChange,
)
from src.app.core.constants import (
    MIN_AGE,
    MAX_AGE,
    MIN_HEIGHT_CM,
    MAX_HEIGHT_CM,
    MIN_WEIGHT_KG,
    MAX_WEIGHT_KG,
)


# Тесты для UserBaseIn
class TestUserBaseIn:
    def test_valid_data(self, base_user_data):
        user = UserBaseIn(**base_user_data)
        assert user.username == base_user_data["username"]
        assert user.email == base_user_data["email"]

    @pytest.mark.parametrize("username", ["ab", "a" * 21, "", "  "])
    def test_invalid_username_length(self, base_user_data, username):
        with pytest.raises(ValidationError):
            UserBaseIn(**{**base_user_data, "username": username})

    @pytest.mark.parametrize("email", ["invalid-email", "@example.com", "test@"])
    def test_invalid_email(self, base_user_data, email):
        with pytest.raises(ValidationError):
            UserBaseIn(**{**base_user_data, "email": email})


# Тесты для UserCreate
class TestUserCreate:
    def test_valid_password(self, base_user_data):
        user_data = base_user_data.copy()
        user_data["password"] = "Str0ngP@ss!"  # Plain string
        user = UserCreate(**user_data)
        assert user.password == "Str0ngP@ss!"  # Direct string comparison

    @pytest.mark.parametrize(
        "password",
        [
            "short",  # Too short
            "nopass",  # No digits or special chars
            "12345678",  # Only digits
            "password",  # Only letters
            "PASSWORD",  # Only uppercase
        ],
    )
    def test_invalid_password(self, base_user_data, password):
        # Create a copy of base_user_data and update password
        user_data = base_user_data.copy()
        user_data["password"] = password  # Plain string
        with pytest.raises(ValidationError):
            UserCreate(**user_data)


# Тесты для UserProfile
class TestUserProfile:
    @pytest.fixture
    def profile_data(self, base_user_data):
        return {
            **base_user_data,
            "id": 1,
            "uid": "abc123",
            "created_at": datetime.now(),
            "is_subscribed": False,
        }

    @pytest.mark.parametrize(
        "age,valid",
        [(MIN_AGE, True), (MAX_AGE, True), (MIN_AGE - 1, False), (MAX_AGE + 1, False)],
    )
    def test_age_validation(self, profile_data, age, valid):
        if valid:
            profile = UserProfile(**{**profile_data, "age": age})
            assert profile.age == age
        else:
            with pytest.raises(ValidationError):
                UserProfile(**{**profile_data, "age": age})

    @pytest.mark.parametrize(
        "weight,valid",
        [
            (MIN_WEIGHT_KG, True),
            (MAX_WEIGHT_KG, True),
            (MIN_WEIGHT_KG - 0.1, False),
            (MAX_WEIGHT_KG + 0.1, False),
        ],
    )
    def test_weight_validation(self, profile_data, weight, valid):
        if valid:
            profile = UserProfile(**{**profile_data, "weight": weight})
            assert profile.weight == weight
        else:
            with pytest.raises(ValidationError):
                UserProfile(**{**profile_data, "weight": weight})

    @pytest.mark.parametrize(
        "height,valid",
        [
            (MIN_HEIGHT_CM, True),
            (MAX_HEIGHT_CM, True),
            (MIN_HEIGHT_CM - 0.1, False),
            (MAX_HEIGHT_CM + 0.1, False),
        ],
    )
    def test_height_validation(self, profile_data, height, valid):
        if valid:
            profile = UserProfile(**{**profile_data, "height": height})
            assert profile.height == height
        else:
            with pytest.raises(ValidationError):
                UserProfile(**{**profile_data, "height": height})


# Тесты для UserProfileUpdate
class TestUserProfileUpdate:

    def test_partial_update(self):
        # Указываем и возраст, и вес, чтобы пройти валидацию
        update = UserProfileUpdate(age=25, weight=70.0)
        assert update.age == 25
        assert update.weight == 70.0

    def test_validation_consistency(self):
        # Должна быть ошибка, если указан возраст, но не указан вес
        with pytest.raises(ValueError) as exc_info:
            UserProfileUpdate(age=25, weight=None)
        assert "указан возраст, укажите вес" in str(exc_info.value).lower()


# Тесты для PasswordChange
class TestPasswordChange:
    def test_password_must_be_different(self):
        # Test that new password must be different from current password
        with pytest.raises(ValidationError) as exc_info:
            PasswordChange(
                current_password="SamePass123!",
                new_password="SamePass123!",  # Same password
            )
        error_msg = str(exc_info.value)
        assert "Новый пароль должен отличаться от текущего" in error_msg

    def test_password_strength(self):
        # Test with a password that's long enough but doesn't meet complexity
        with pytest.raises(ValidationError) as exc_info:
            PasswordChange(
                current_password="Oldpass123!",
                new_password="weakpassword",  # Long but no uppercase/number
            )
        error_msg = str(exc_info.value).lower()
        # Check for any of the validation messages
        assert any(
            msg in error_msg
            for msg in ["uppercase", "digit", "number", "заглавные", "цифры"]
        )

    def test_successful_password_change(self):
        # Test successful password change with valid passwords
        password_change = PasswordChange(
            current_password="OldPass123!",
            new_password="NewPass123!",  # Valid password
        )

        # Verify the new password is set correctly
        assert password_change.new_password == "NewPass123!"
        assert password_change.current_password == "OldPass123!"


# Тесты для сериализации
class TestSerialization:
    def test_public_user_serialization(self):
        user = UserPublic(
            id=1,
            uid="abc123",
            username="testuser",
            email="test@example.com",
            hashed_password=b"hashed",
        )
        data = user.model_dump()
        assert "hashed_password" not in data
        assert data["username"] == "testuser"

    def test_profile_serialization(self):
        profile = UserProfile(
            id=1,
            uid="abc123",
            username="testuser",
            email="test@example.com",
            created_at=datetime(2023, 1, 1),
            is_subscribed=False,
            gender="male",
            age=25,
        )
        data = profile.model_dump()
        assert data["age"] == 25
        assert data["gender"] == "male"
