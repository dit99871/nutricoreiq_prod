"""
Тесты для UserService.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import Request, status
from fastapi.responses import JSONResponse
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.core.exceptions import AuthenticationError, DatabaseError, ExpiredTokenException, UserAlreadyExistsError
from src.app.core.models.user import GoalType, KFALevel, UserRole
from src.app.core.schemas.user import PasswordChange, UserCreate, UserProfile, UserPublic
from src.app.core.services.user_service import UserService, get_user_service


@pytest.fixture
def mock_session():
    """Создает мок для AsyncSession."""
    session = AsyncMock(spec=AsyncSession)
    return session


@pytest.fixture
def user_public():
    """Валидные данные публичного пользователя."""
    return UserPublic(
        id=1,
        uid="test-uid-123",
        username="testuser",
        email="test@example.com",
    )


@pytest.fixture
def user_create():
    """Валидные данные для создания пользователя."""
    return UserCreate(
        username="newuser",
        email="new@example.com",
        password="SecurePass123!",
    )


@pytest.fixture
def user_profile():
    """Валидные данные профиля пользователя."""
    from datetime import datetime
    return UserProfile(
        id=1,
        uid="test-uid-123",
        username="testuser",
        email="test@example.com",
        gender="male",
        age=30,
        weight=75.0,
        height=180.0,
        kfa=KFALevel.MEDIUM,
        goal=GoalType.MAINTAIN_WEIGHT,
        created_at=datetime.now(),
        is_subscribed=False,
    )


@pytest.fixture
def password_change():
    """Валидные данные для смены пароля."""
    return PasswordChange(
        current_password="OldPass123!",
        new_password="NewPass123!",
    )


@pytest.fixture
def mock_request():
    """Создает мок для Request."""
    request = MagicMock(spec=Request)
    request.client = MagicMock()
    request.client.host = "192.168.1.1"
    request.cookies = {}
    return request


@pytest.fixture
def mock_redis():
    """Создает мок для Redis."""
    redis = AsyncMock(spec=Redis)
    return redis


@pytest.fixture
def user_service(mock_session):
    """Создает экземпляр UserService."""
    return UserService(session=mock_session)


# --- authenticate_user ---


@pytest.mark.asyncio
@patch("src.app.core.services.user_service.get_user_by_name")
@patch("src.app.core.services.user_service.verify_password")
async def test_authenticate_user_success(mock_verify_password, mock_get_user_by_name, mock_session):
    """Тест успешной аутентификации пользователя."""
    mock_user = MagicMock()
    mock_user.uid = "test-uid"
    mock_user.hashed_password = "hashed_password"
    mock_user.username = "testuser"
    mock_user.email = "test@example.com"
    mock_user.id = 1
    mock_get_user_by_name.return_value = mock_user
    mock_verify_password.return_value = True

    result = await UserService.authenticate_user(mock_session, "testuser", "password")

    assert isinstance(result, UserPublic)


@pytest.mark.asyncio
@patch("src.app.core.services.user_service.get_user_by_name")
async def test_authenticate_user_user_not_found(mock_get_user_by_name, mock_session):
    """Тест аутентификации несуществующего пользователя."""
    mock_get_user_by_name.return_value = None

    with pytest.raises(AuthenticationError) as exc_info:
        await UserService.authenticate_user(mock_session, "nonexistent", "password")

    assert "Неверные учетные данные" in str(exc_info.value)


@pytest.mark.asyncio
@patch("src.app.core.services.user_service.get_user_by_name")
@patch("src.app.core.services.user_service.verify_password")
@patch("src.app.core.services.user_service.needs_rehash")
@patch("src.app.core.services.user_service.update_user_password")
async def test_authenticate_user_with_rehash(mock_update_password, mock_needs_rehash, mock_verify_password, mock_get_user_by_name, mock_session):
    """Тест аутентификации с миграцией хеша пароля."""
    mock_user = MagicMock()
    mock_user.uid = "test-uid"
    mock_user.hashed_password = "old_hash"
    mock_user.username = "testuser"
    mock_user.email = "test@example.com"
    mock_user.id = 1
    mock_get_user_by_name.return_value = mock_user
    mock_verify_password.return_value = False
    mock_needs_rehash.return_value = True
    mock_update_password.return_value = None

    result = await UserService.authenticate_user(mock_session, "testuser", "password")

    assert isinstance(result, UserPublic)
    mock_update_password.assert_called_once()


@pytest.mark.asyncio
@patch("src.app.core.services.user_service.get_user_by_name")
@patch("src.app.core.services.user_service.verify_password")
@patch("src.app.core.services.user_service.needs_rehash")
async def test_authenticate_user_wrong_password(mock_needs_rehash, mock_verify_password, mock_get_user_by_name, mock_session):
    """Тест аутентификации с неверным паролем."""
    mock_user = MagicMock()
    mock_user.hashed_password = "hashed_password"
    mock_get_user_by_name.return_value = mock_user
    mock_verify_password.return_value = False
    mock_needs_rehash.return_value = False

    with pytest.raises(AuthenticationError) as exc_info:
        await UserService.authenticate_user(mock_session, "testuser", "wrong_password")

    assert "Введён неверный пароль" in str(exc_info.value)


# --- register_user ---


@pytest.mark.asyncio
@patch("src.app.core.services.user_service.UserService._send_welcome_email")
@patch("src.app.core.services.user_service.create_user")
@patch("src.app.core.services.user_service.get_user_by_email")
@patch("src.app.core.services.user_service.get_user_by_name")
async def test_register_user_success(mock_get_user_by_name, mock_get_user_by_email, mock_create_user, mock_send_welcome_email, user_service, user_create, mock_request):
    """Тест успешной регистрации пользователя."""
    mock_get_user_by_name.return_value = None
    mock_get_user_by_email.return_value = None
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.email = "new@example.com"
    mock_user.uid = "test-uid"
    mock_user.username = "newuser"
    mock_user.hashed_password = b"hashed_password"
    mock_create_user.return_value = mock_user
    mock_send_welcome_email.return_value = None

    result = await user_service.register_user(user_create, mock_request)

    assert isinstance(result, UserPublic)
    mock_create_user.assert_called_once()


@pytest.mark.asyncio
@patch("src.app.core.services.user_service.get_user_by_name")
async def test_register_user_username_exists(mock_get_user_by_name, user_service, user_create, mock_request):
    """Тест регистрации с существующим username."""
    mock_get_user_by_name.return_value = MagicMock()

    with pytest.raises(UserAlreadyExistsError):
        await user_service.register_user(user_create, mock_request)


@pytest.mark.asyncio
@patch("src.app.core.services.user_service.get_user_by_name")
@patch("src.app.core.services.user_service.get_user_by_email")
async def test_register_user_email_exists(mock_get_user_by_email, mock_get_user_by_name, user_service, user_create, mock_request):
    """Тест регистрации с существующим email."""
    mock_get_user_by_name.return_value = None
    mock_get_user_by_email.return_value = MagicMock()

    with pytest.raises(UserAlreadyExistsError) as exc_info:
        await user_service.register_user(user_create, mock_request)

    assert "email" in str(exc_info.value).lower()


@pytest.mark.asyncio
@patch("src.app.core.services.user_service.create_user")
@patch("src.app.core.services.user_service.get_user_by_email")
@patch("src.app.core.services.user_service.get_user_by_name")
async def test_register_user_database_error(mock_get_user_by_name, mock_get_user_by_email, mock_create_user, user_service, user_create, mock_request):
    """Тест обработки ошибки базы данных при регистрации."""
    mock_get_user_by_name.return_value = None
    mock_get_user_by_email.return_value = None
    mock_create_user.side_effect = Exception("DB error")

    with pytest.raises(DatabaseError):
        await user_service.register_user(user_create, mock_request)


# --- login ---


@pytest.mark.asyncio
@patch("src.app.core.services.user_service.UserService.authenticate_user")
@patch("src.app.core.services.user_service.create_response")
async def test_login_success(mock_create_response, mock_authenticate_user, user_service, mock_request, mock_session, user_public):
    """Тест успешного входа."""
    mock_authenticate_user.return_value = user_public
    mock_create_response.return_value = JSONResponse(content={"access_token": "token"})

    result = await user_service.login(mock_request, mock_session, "testuser", "password")

    assert isinstance(result, JSONResponse)
    mock_authenticate_user.assert_called_once()


# --- logout ---


@pytest.mark.asyncio
@patch("src.app.core.services.user_service.revoke_refresh_token")
async def test_logout_success(mock_revoke_refresh_token, user_service, mock_request, mock_redis, user_public):
    """Тест успешного выхода."""
    from src.app.core.constants import REFRESH_TOKEN_TYPE
    mock_request.cookies = {REFRESH_TOKEN_TYPE: "refresh_token", "redis_session_id": "session_id"}
    mock_revoke_refresh_token.return_value = None
    mock_redis.delete = AsyncMock()

    result = await user_service.logout(mock_request, mock_redis, user_public)

    assert isinstance(result, JSONResponse)
    assert result.status_code == status.HTTP_200_OK


@pytest.mark.asyncio
async def test_logout_no_user(user_service, mock_request, mock_redis):
    """Тест выхода без пользователя."""
    with pytest.raises(ExpiredTokenException):
        await user_service.logout(mock_request, mock_redis, None)


@pytest.mark.asyncio
async def test_logout_no_refresh_token(user_service, mock_request, mock_redis, user_public):
    """Тест выхода без refresh токена."""
    mock_request.cookies = {}

    with pytest.raises(ExpiredTokenException):
        await user_service.logout(mock_request, mock_redis, user_public)


# --- _send_welcome_email ---


@pytest.mark.asyncio
@patch("src.app.core.services.user_service.settings")
@patch("src.app.core.services.user_service.send_welcome")
async def test_send_welcome_email_dev(mock_send_welcome, mock_settings, user_public):
    """Тест отправки приветственного письма в деве."""
    mock_settings.env.env = "dev"
    mock_send_welcome.return_value = None

    await UserService._send_welcome_email(user_public)

    mock_send_welcome.assert_called_once()


@pytest.mark.asyncio
@patch("src.app.core.services.user_service.settings")
@patch("src.app.core.services.user_service.send_welcome_email")
async def test_send_welcome_email_prod(mock_send_welcome_email, mock_settings, user_public):
    """Тест отправки приветственного письмо в проде."""
    mock_settings.env.env = "prod"
    mock_send_welcome_email.kiq = AsyncMock()

    await UserService._send_welcome_email(user_public)

    mock_send_welcome_email.kiq.assert_called_once()


@pytest.mark.asyncio
@patch("src.app.core.services.user_service.settings")
@patch("src.app.core.services.user_service.send_welcome")
async def test_send_welcome_email_error(mock_send_welcome, mock_settings, user_public):
    """Тест обработки ошибки при отправке письма."""
    mock_settings.env.env = "dev"
    mock_send_welcome.side_effect = Exception("Email error")

    # Не должно выбрасывать исключение
    await UserService._send_welcome_email(user_public)


# --- change_password ---


@pytest.mark.asyncio
@patch("src.app.core.services.user_service.UserService.authenticate_user")
@patch("src.app.core.services.user_service.update_user_password")
@patch("src.app.core.services.user_service.revoke_all_refresh_tokens")
@patch("src.app.core.services.user_service.create_response")
async def test_change_password_success(mock_create_response, mock_revoke_all, mock_update_password, mock_authenticate_user, user_service, mock_request, mock_session, user_public, password_change):
    """Тест успешной смены пароля."""
    mock_authenticate_user.return_value = user_public
    mock_update_password.return_value = None
    mock_revoke_all.return_value = None
    mock_create_response.return_value = JSONResponse(content={"access_token": "token"})

    result = await user_service.change_password(mock_request, mock_session, user_public, password_change)

    assert isinstance(result, JSONResponse)
    mock_update_password.assert_called_once()
    mock_revoke_all.assert_called_once()


# --- get_user_by_access_jwt ---


@pytest.mark.asyncio
@patch("src.app.core.services.user_service.get_jwt_payload")
@patch("src.app.core.services.user_service.get_user_by_uid")
async def test_get_user_by_access_jwt_success(mock_get_user_by_uid, mock_get_jwt_payload, mock_session, user_public):
    """Тест успешного получения пользователя по access токену."""
    from src.app.core.constants import TOKEN_TYPE_FIELD, ACCESS_TOKEN_TYPE
    mock_get_jwt_payload.return_value = {"sub": "test-uid", TOKEN_TYPE_FIELD: ACCESS_TOKEN_TYPE}
    mock_get_user_by_uid.return_value = user_public

    result = await UserService.get_user_by_access_jwt(mock_session, "valid_token")

    assert isinstance(result, UserPublic)


@pytest.mark.asyncio
async def test_get_user_by_access_jwt_none_token(mock_session):
    """Тест когда токен None."""
    result = await UserService.get_user_by_access_jwt(mock_session, None)

    assert result is None


@pytest.mark.asyncio
@patch("src.app.core.services.user_service.get_jwt_payload")
async def test_get_user_by_access_jwt_wrong_token_type(mock_get_jwt_payload, mock_session):
    """Тест с неверным типом токена."""
    mock_get_jwt_payload.return_value = {"sub": "test-uid", "type": "refresh"}

    with pytest.raises(Exception):  # CREDENTIAL_EXCEPTION
        await UserService.get_user_by_access_jwt(mock_session, "token")


@pytest.mark.asyncio
@patch("src.app.core.services.user_service.get_jwt_payload")
async def test_get_user_by_access_jwt_no_sub(mock_get_jwt_payload, mock_session):
    """Тест когда sub отсутствует в payload."""
    from src.app.core.constants import TOKEN_TYPE_FIELD, ACCESS_TOKEN_TYPE
    mock_get_jwt_payload.return_value = {TOKEN_TYPE_FIELD: ACCESS_TOKEN_TYPE}

    with pytest.raises(Exception):  # CREDENTIAL_EXCEPTION
        await UserService.get_user_by_access_jwt(mock_session, "token")


# --- refresh_jwt ---


@pytest.mark.asyncio
@patch("src.app.core.services.user_service.create_response")
@patch("src.app.core.services.user_service.get_user_by_uid")
@patch("src.app.core.services.user_service.validate_refresh_jwt")
@patch("src.app.core.services.user_service.get_jwt_payload")
@patch("src.app.core.services.user_service.get_jwt_from_cookies")
async def test_refresh_jwt_success(mock_get_jwt_from_cookies, mock_get_jwt_payload, mock_validate, mock_get_user_by_uid, mock_create_response, user_service, mock_request, mock_session, mock_redis, user_public):
    """Тест успешного обновления токенов."""
    mock_get_jwt_from_cookies.return_value = "refresh_token"
    mock_get_jwt_payload.return_value = {"sub": "test-uid"}
    mock_validate.return_value = True
    mock_get_user_by_uid.return_value = user_public
    mock_create_response.return_value = JSONResponse(content={"access_token": "new_token"})

    result = await user_service.refresh_jwt(mock_request, mock_session, mock_redis)

    assert isinstance(result, JSONResponse)


@pytest.mark.asyncio
@patch("src.app.core.services.user_service.get_jwt_from_cookies")
async def test_refresh_jwt_no_token(mock_get_jwt_from_cookies, user_service, mock_request, mock_session, mock_redis):
    """Тест обновления токенов без refresh токена."""
    mock_get_jwt_from_cookies.return_value = None

    with pytest.raises(AuthenticationError):
        await user_service.refresh_jwt(mock_request, mock_session, mock_redis)


@pytest.mark.asyncio
@patch("src.app.core.services.user_service.get_jwt_payload")
@patch("src.app.core.services.user_service.get_jwt_from_cookies")
async def test_refresh_jwt_no_sub(mock_get_jwt_from_cookies, mock_get_jwt_payload, user_service, mock_request, mock_session, mock_redis):
    """Тест обновления токенов без sub в payload."""
    mock_get_jwt_from_cookies.return_value = "refresh_token"
    mock_get_jwt_payload.return_value = {}

    with pytest.raises(Exception):  # CREDENTIAL_EXCEPTION
        await user_service.refresh_jwt(mock_request, mock_session, mock_redis)


@pytest.mark.asyncio
@patch("src.app.core.services.user_service.validate_refresh_jwt")
@patch("src.app.core.services.user_service.get_jwt_payload")
@patch("src.app.core.services.user_service.get_jwt_from_cookies")
async def test_refresh_jwt_invalid_token(mock_get_jwt_from_cookies, mock_get_jwt_payload, mock_validate, user_service, mock_request, mock_session, mock_redis):
    """Тест обновления токенов с невалидным токеном."""
    mock_get_jwt_from_cookies.return_value = "refresh_token"
    mock_get_jwt_payload.return_value = {"sub": "test-uid"}
    mock_validate.return_value = False

    with pytest.raises(Exception):  # CREDENTIAL_EXCEPTION
        await user_service.refresh_jwt(mock_request, mock_session, mock_redis)


# --- calculate_user_nutrients ---


@pytest.mark.asyncio
@patch("src.app.core.services.user_service.HealthCalculator.calculate_adjusted_tdee")
@patch("src.app.core.services.user_service.HealthCalculator.calculate_nutrients")
async def test_calculate_user_nutrients_success(mock_calculate_nutrients, mock_calculate_tdee, user_service, user_profile):
    """Тест успешного расчета нутриентов."""
    mock_calculate_tdee.return_value = 2500.0
    mock_calculate_nutrients.return_value = {"protein": 150, "carbs": 300}

    result = user_service.calculate_user_nutrients(user_profile)

    assert result is not None
    assert result["tdee"] == 2500.0
    assert "nutrients" in result


def test_calculate_user_nutrients_incomplete_profile(user_service):
    """Тест расчета нутриентов с незаполненным профилем."""
    from datetime import datetime
    incomplete_profile = UserProfile(
        id=1,
        uid="test-uid",
        username="testuser",
        email="test@example.com",
        gender=None,
        age=30,
        weight=75.0,
        height=180.0,
        kfa=KFALevel.MEDIUM,
        goal=GoalType.MAINTAIN_WEIGHT,
        created_at=datetime.now(),
        is_subscribed=False,
    )

    result = user_service.calculate_user_nutrients(incomplete_profile)

    assert result is None


@pytest.mark.asyncio
@patch("src.app.core.services.user_service.HealthCalculator.calculate_adjusted_tdee")
async def test_calculate_user_nutrients_calculation_error(mock_calculate_tdee, user_service, user_profile):
    """Тест обработки ошибки при расчете."""
    mock_calculate_tdee.side_effect = ValueError("Calculation error")

    result = user_service.calculate_user_nutrients(user_profile)

    assert result is None


# --- get_user_service ---


def test_get_user_service(mock_session):
    """Тест фабрики UserService."""
    service = get_user_service(mock_session)

    assert isinstance(service, UserService)
    assert service.session == mock_session
