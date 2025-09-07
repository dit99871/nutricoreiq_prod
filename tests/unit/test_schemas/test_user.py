import pytest
from datetime import datetime
from pydantic import ValidationError, SecretStr
from enum import Enum


# Мокаем валидатор пароля
def mock_validate_password_strength(v):
    if isinstance(v, SecretStr):
        v = v.get_secret_value()
    # Простая проверка сложности пароля
    if len(v) < 8:
        raise ValueError("Пароль слишком короткий")
    if not any(c.islower() for c in v):
        raise ValueError("Пароль должен содержать строчные буквы")
    if not any(c.isupper() for c in v):
        raise ValueError("Пароль должен содержать заглавные буквы")
    if not any(c.isdigit() for c in v):
        raise ValueError("Пароль должен содержать цифры")
    return SecretStr(v)


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
        user = UserCreate(**{**base_user_data, "password": "Str0ngP@ss!"})
        assert user.password.get_secret_value() == "Str0ngP@ss!"

    @pytest.mark.parametrize(
        "password",
        [
            "short",  # Слишком короткий
            "nopass",  # Нет цифр и спецсимволов
            "12345678",  # Только цифры
            "password",  # Только буквы
            "PASSWORD",  # Только заглавные
        ],
    )
    def test_invalid_password(self, base_user_data, password):
        with pytest.raises(ValidationError):
            UserCreate(**{**base_user_data, "password": password})


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
        # This should now work with the fixed schema
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
        error_msg = str(exc_info.value)
        # Check for any of the validation messages
        assert any(
            msg in error_msg.lower()
            for msg in ["uppercase", "digit", "number", "заглавные", "цифры"]
        )

    def test_successful_password_change(self):
        password_change = PasswordChange(
            current_password="OldPass123!", new_password="NewPass123!"  # Valid password
        )
        # Use get_secret_value() to compare SecretStr
        assert password_change.new_password.get_secret_value() == "NewPass123!"


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
