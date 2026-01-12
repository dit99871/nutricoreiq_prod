"""
Тесты для схем пользователя.
"""

import pytest
from datetime import datetime
from pydantic import ValidationError

from src.app.core.schemas import (
    UserBaseIn,
    UserCreate,
    UserPublic,
    UserProfile,
    UserProfileUpdate,
    PasswordChange,
)
from src.app.core.models.user import KFALevel, GoalType
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

    @pytest.mark.parametrize("username", ["ab", "a" * 21, ""])
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
        """Тест с валидным паролем (заглавные, строчные, цифры, спецсимволы)"""
        user_data = base_user_data.copy()
        user_data["password"] = "Str0ngP@ss!"
        user = UserCreate(**user_data)
        assert user.password == "Str0ngP@ss!"

    def test_password_too_short(self, base_user_data):
        """Тест с коротким паролем (< 8 символов)"""
        user_data = base_user_data.copy()
        user_data["password"] = "Short1!"
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(**user_data)
        print(exc_info.value)
        assert "at least 8 characters" in str(exc_info.value).lower()

    def test_password_no_uppercase(self, base_user_data):
        """Тест без заглавных букв"""
        user_data = base_user_data.copy()
        user_data["password"] = "noupperca5e!"
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(**user_data)
        error_msg = str(exc_info.value).lower()
        assert "прописные" in error_msg or "uppercase" in error_msg

    def test_password_no_lowercase(self, base_user_data):
        """Тест без строчных букв"""
        user_data = base_user_data.copy()
        user_data["password"] = "NOLOWERCASE5!"
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(**user_data)
        error_msg = str(exc_info.value).lower()
        assert "строчные" in error_msg or "lowercase" in error_msg

    def test_password_no_digit(self, base_user_data):
        """Тест без цифр"""
        user_data = base_user_data.copy()
        user_data["password"] = "NoDigits!@#"
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(**user_data)
        error_msg = str(exc_info.value).lower()
        assert "цифр" in error_msg or "digit" in error_msg

    def test_password_no_special(self, base_user_data):
        """Тест без спецсимволов"""
        user_data = base_user_data.copy()
        user_data["password"] = "NoSpecial123"
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(**user_data)
        error_msg = str(exc_info.value).lower()
        assert "спецсимвол" in error_msg or "special" in error_msg


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
        """Тест частичного обновления (возраст + вес)"""
        update = UserProfileUpdate(age=25, weight=70.0)
        assert update.age == 25
        assert update.weight == 70.0

    def test_validation_consistency(self):
        """Тест кросс-валидации: если указан возраст, нужен вес"""
        with pytest.raises(ValueError) as exc_info:
            UserProfileUpdate(age=25, weight=None)
        assert "указан возраст, укажите вес" in str(exc_info.value).lower()

    def test_kfa_coercion_from_int(self):
        """Тест преобразования int в KFALevel"""
        update = UserProfileUpdate(kfa=3)
        assert update.kfa == KFALevel.MEDIUM

    def test_goal_coercion(self):
        """Тест преобразования строки в GoalType"""
        update = UserProfileUpdate(goal=GoalType.LOSE_WEIGHT)
        assert update.goal == GoalType.LOSE_WEIGHT


# Тесты для PasswordChange
class TestPasswordChange:
    def test_password_must_be_different(self):
        """Тест что новый пароль должен отличаться от текущего"""
        with pytest.raises(ValidationError) as exc_info:
            PasswordChange(
                current_password="SamePass123!",
                new_password="SamePass123!",
            )
        error_msg = str(exc_info.value)
        assert "Новый пароль должен отличаться от текущего" in error_msg

    def test_new_password_strength_validation(self):
        """Тест валидации сложности нового пароля"""
        with pytest.raises(ValidationError) as exc_info:
            PasswordChange(
                current_password="OldPass123!",
                new_password="weakpassword",  # Нет заглавных, цифр, спецсимволов
            )
        error_msg = str(exc_info.value).lower()
        # Проверяем что есть хоть одно из требований
        assert any(
            msg in error_msg
            for msg in ["uppercase", "digit", "заглавн", "цифр", "спецсимвол"]
        )

    def test_successful_password_change(self):
        """Тест успешной смены пароля"""
        password_change = PasswordChange(
            current_password="OldPass123!",
            new_password="NewPass456@",
        )
        assert password_change.new_password == "NewPass456@"
        assert password_change.current_password == "OldPass123!"


# Тесты для сериализации
class TestSerialization:
    def test_public_user_serialization(self):
        """Тест что hashed_password исключается из сериализации"""
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
        """Тест сериализации профиля"""
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
