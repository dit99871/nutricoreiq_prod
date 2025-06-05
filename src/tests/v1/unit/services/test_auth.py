import pytest
from unittest.mock import AsyncMock, Mock, patch
from fastapi import HTTPException, status
from fastapi.responses import ORJSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.services.auth import (
    get_access_token_from_cookies,
    get_current_token_payload,
    create_jwt,
    create_access_jwt,
    create_refresh_jwt,
    update_password,
    add_tokens_to_response,
    get_current_auth_user,
    get_current_auth_user_for_refresh,
    authenticate_user,
    CREDENTIAL_EXCEPTION,
    ACCESS_TOKEN_TYPE,
    REFRESH_TOKEN_TYPE,
    TOKEN_TYPE_FIELD,
)
from src.app.schemas.user import UserResponse


# Фикстура для создания тестового пользователя
@pytest.fixture
def mock_user():
    user = Mock(spec=UserResponse)
    user.uid = "user123"
    user.username = "testuser"
    user.email = "test@example.com"
    user.hashed_password = b"hashed_password"
    return user


# Фикстура для создания тестового запроса
@pytest.fixture
def mock_request():
    request = Mock()
    return request


# Тесты для get_access_token_from_cookies
@pytest.mark.asyncio
async def test_get_access_token_from_cookies_present(mock_request):
    mock_request.cookies = {"access_token": "test_token"}
    token = await get_access_token_from_cookies(mock_request)
    assert token == "test_token"


@pytest.mark.asyncio
async def test_get_access_token_from_cookies_missing(mock_request):
    mock_request.cookies = {}
    token = await get_access_token_from_cookies(mock_request)
    assert token is None


# Тесты для get_current_token_payload
def test_get_current_token_payload_valid():
    token = "valid.token"
    payload = {TOKEN_TYPE_FIELD: ACCESS_TOKEN_TYPE, "sub": "user123"}
    with patch("src.app.services.auth.decode_jwt", return_value=payload):
        result = get_current_token_payload(token)
    assert result == payload


def test_get_current_token_payload_invalid_none():
    token = "invalid.token"
    with patch("src.app.services.auth.decode_jwt", return_value=None):
        with pytest.raises(HTTPException) as exc:
            get_current_token_payload(token)
        assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert exc.value.detail == "Could not validate credentials"


def test_get_current_token_payload_wrong_type():
    token = "wrong_type.token"
    payload = {TOKEN_TYPE_FIELD: "wrong_type", "sub": "user123"}
    with patch("src.app.services.auth.decode_jwt", return_value=payload):
        with pytest.raises(HTTPException) as exc:
            get_current_token_payload(token)
        assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Invalid token type" in exc.value.detail


def test_get_current_token_payload_missing_sub():
    token = "missing_sub.token"
    payload = {TOKEN_TYPE_FIELD: ACCESS_TOKEN_TYPE}
    with patch("src.app.services.auth.decode_jwt", return_value=payload):
        with pytest.raises(HTTPException) as exc:
            get_current_token_payload(token)
        assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert exc.value.detail == "Could not validate credentials"


# Тесты для create_jwt
def test_create_jwt_success():
    token_type = ACCESS_TOKEN_TYPE
    token_data = {"sub": "user123"}
    with patch("src.app.services.auth.encode_jwt", return_value="encoded.token"):
        token = create_jwt(token_type, token_data, expire_minutes=15)
    assert token == "encoded.token"


def test_create_jwt_encoding_error():
    token_type = ACCESS_TOKEN_TYPE
    token_data = {"sub": "user123"}
    with patch(
        "src.app.services.auth.encode_jwt",
        side_effect=HTTPException(status_code=401, detail="Encoding error"),
    ):
        with pytest.raises(HTTPException) as exc:
            create_jwt(token_type, token_data)
        assert exc.value.status_code == 401
        assert exc.value.detail == "Encoding error"


# Тесты для create_access_jwt
def test_create_access_jwt_success(mock_user):
    user = mock_user
    with patch("src.app.services.auth.create_jwt", return_value="access.token"):
        token = create_access_jwt(user)
    assert token == "access.token"


def test_create_access_jwt_error(mock_user):
    user = mock_user
    with patch(
        "src.app.services.auth.create_jwt",
        side_effect=HTTPException(status_code=401, detail="JWT error"),
    ):
        with pytest.raises(HTTPException) as exc:
            create_access_jwt(user)
        assert exc.value.status_code == 401
        assert exc.value.detail == "JWT error"


# Тесты для create_refresh_jwt
@pytest.mark.asyncio
async def test_create_refresh_jwt_success(mock_user):
    user = mock_user
    with patch("src.app.services.auth.create_jwt", return_value="refresh.token"), patch(
        "src.app.services.auth.add_refresh_to_redis", new_callable=AsyncMock
    ):
        token = await create_refresh_jwt(user)
    assert token == "refresh.token"


@pytest.mark.asyncio
async def test_create_refresh_jwt_jwt_error(mock_user):
    user = mock_user
    with patch(
        "src.app.services.auth.create_jwt",
        side_effect=HTTPException(status_code=401, detail="JWT error"),
    ):
        with pytest.raises(HTTPException) as exc:
            await create_refresh_jwt(user)
        assert exc.value.status_code == 401
        assert exc.value.detail == "JWT error"


@pytest.mark.asyncio
async def test_create_refresh_jwt_redis_error(mock_user):
    user = mock_user
    with patch("src.app.services.auth.create_jwt", return_value="refresh.token"), patch(
        "src.app.services.auth.add_refresh_to_redis",
        side_effect=Exception("Redis error"),
    ):
        with pytest.raises(HTTPException) as exc:
            await create_refresh_jwt(user)
        assert exc.value.status_code == 401
        assert exc.value.detail == "Redis error"


# Тесты для update_password
@pytest.mark.asyncio
async def test_update_password_success(mock_user):
    user = mock_user
    response = ORJSONResponse(status_code=200, content={"message": "Success"})
    with patch(
        "src.app.services.auth.revoke_all_refresh_tokens", new_callable=AsyncMock
    ), patch(
        "src.app.services.auth.add_tokens_to_response",
        new_callable=AsyncMock,
        return_value=response,
    ):
        result = await update_password(user)
    assert result == response


@pytest.mark.asyncio
async def test_update_password_error(mock_user):
    user = mock_user
    with patch(
        "src.app.services.auth.revoke_all_refresh_tokens", new_callable=AsyncMock
    ), patch(
        "src.app.services.auth.add_tokens_to_response",
        side_effect=HTTPException(status_code=401, detail="Error"),
    ):
        with pytest.raises(HTTPException) as exc:
            await update_password(user)
        assert exc.value.status_code == 401
        assert exc.value.detail == "Error"


# Тесты для add_tokens_to_response
@pytest.mark.asyncio
async def test_add_tokens_to_response_success(mock_user):
    user = mock_user
    response = ORJSONResponse(status_code=200, content={"message": "Success"})
    with patch(
        "src.app.services.auth.create_access_jwt", return_value="access.token"
    ), patch(
        "src.app.services.auth.create_refresh_jwt",
        new_callable=AsyncMock,
        return_value="refresh.token",
    ), patch(
        "src.app.services.auth.create_response", return_value=response
    ):
        result = await add_tokens_to_response(user)
    assert result == response


@pytest.mark.asyncio
async def test_add_tokens_to_response_error(mock_user):
    user = mock_user
    with patch(
        "src.app.services.auth.create_access_jwt", return_value="access.token"
    ), patch(
        "src.app.services.auth.create_refresh_jwt",
        side_effect=HTTPException(status_code=401, detail="Error"),
    ):
        with pytest.raises(HTTPException) as exc:
            await add_tokens_to_response(user)
        assert exc.value.status_code == 401
        assert exc.value.detail == "Error"


# Тесты для get_current_auth_user
@pytest.mark.asyncio
async def test_get_current_auth_user_no_token():
    token = None
    session = AsyncMock(spec=AsyncSession)
    user = await get_current_auth_user(token, session)
    assert user is None


@pytest.mark.asyncio
async def test_get_current_auth_user_valid_token(mock_user):
    token = "valid.token"
    user = mock_user
    with patch(
        "src.app.services.auth.get_current_token_payload",
        return_value={"sub": "user123"},
    ), patch(
        "src.app.services.auth.get_user_by_uid",
        new_callable=AsyncMock,
        return_value=user,
    ):
        result = await get_current_auth_user(token, AsyncMock(spec=AsyncSession))
    assert result == user


@pytest.mark.asyncio
async def test_get_current_auth_user_invalid_token():
    token = "invalid.token"
    with patch(
        "src.app.services.auth.get_current_token_payload",
        side_effect=CREDENTIAL_EXCEPTION,
    ):
        with pytest.raises(HTTPException) as exc:
            await get_current_auth_user(token, AsyncMock(spec=AsyncSession))
        assert exc.value.status_code == 401
        assert exc.value.detail == "Could not validate credentials"


@pytest.mark.asyncio
async def test_get_current_auth_user_user_not_found():
    token = "valid.token"
    with patch(
        "src.app.services.auth.get_current_token_payload",
        return_value={"sub": "user123"},
    ), patch(
        "src.app.services.auth.get_user_by_uid",
        new_callable=AsyncMock,
        return_value=None,
    ):
        with pytest.raises(HTTPException) as exc:
            await get_current_auth_user(token, AsyncMock(spec=AsyncSession))
        assert exc.value.status_code == 401
        assert exc.value.detail == "Could not validate credentials"


# Тесты для get_current_auth_user_for_refresh
@pytest.mark.asyncio
async def test_get_current_auth_user_for_refresh_valid(mock_user):
    token = "refresh.token"
    user = mock_user
    session = AsyncMock(spec=AsyncSession)
    redis = AsyncMock()
    with patch(
        "src.app.services.auth.decode_jwt", return_value={"sub": "user123"}
    ), patch(
        "src.app.services.auth.validate_refresh_jwt",
        new_callable=AsyncMock,
        return_value=True,
    ), patch(
        "src.app.services.auth.get_user_by_uid",
        new_callable=AsyncMock,
        return_value=user,
    ):
        result = await get_current_auth_user_for_refresh(token, session, redis)
    assert result == user


@pytest.mark.asyncio
async def test_get_current_auth_user_for_refresh_invalid_token():
    token = "invalid.token"
    session = AsyncMock(spec=AsyncSession)
    redis = AsyncMock()
    with patch("src.app.services.auth.decode_jwt", return_value=None):
        with pytest.raises(HTTPException) as exc:
            await get_current_auth_user_for_refresh(token, session, redis)
        assert exc.value.status_code == 401
        assert exc.value.detail == "Failed to decode refresh token"


@pytest.mark.asyncio
async def test_get_current_auth_user_for_refresh_missing_sub():
    token = "missing_sub.token"
    session = AsyncMock(spec=AsyncSession)
    redis = AsyncMock()
    with patch(
        "src.app.services.auth.decode_jwt",
        return_value={TOKEN_TYPE_FIELD: REFRESH_TOKEN_TYPE},
    ):
        with pytest.raises(HTTPException) as exc:
            await get_current_auth_user_for_refresh(token, session, redis)
        assert exc.value.status_code == 401
        assert exc.value.detail == "User id not found in refresh token"


@pytest.mark.asyncio
async def test_get_current_auth_user_for_refresh_invalid_redis():
    token = "invalid_redis.token"
    session = AsyncMock(spec=AsyncSession)
    redis = AsyncMock()
    with patch(
        "src.app.services.auth.decode_jwt", return_value={"sub": "user123"}
    ), patch(
        "src.app.services.auth.validate_refresh_jwt",
        new_callable=AsyncMock,
        return_value=False,
    ):
        with pytest.raises(HTTPException) as exc:
            await get_current_auth_user_for_refresh(token, session, redis)
        assert exc.value.status_code == 401
        assert exc.value.detail == "Refresh token is invalid or has expired"


# Тесты для authenticate_user
@pytest.mark.asyncio
async def test_authenticate_user_success(mock_user):
    user = mock_user
    session = AsyncMock(spec=AsyncSession)
    with patch(
        "src.app.services.auth.get_user_by_name",
        new_callable=AsyncMock,
        return_value=user,
    ), patch("src.app.services.auth.verify_password", return_value=True):
        result = await authenticate_user(session, "testuser", "password")
    assert result == UserResponse.model_validate(user)


@pytest.mark.asyncio
async def test_authenticate_user_user_not_found():
    session = AsyncMock(spec=AsyncSession)
    with patch(
        "src.app.services.auth.get_user_by_name",
        new_callable=AsyncMock,
        return_value=None,
    ):
        with pytest.raises(HTTPException) as exc:
            await authenticate_user(session, "testuser", "password")
        assert exc.value.status_code == 401
        assert exc.value.detail == "Invalid email or password"


@pytest.mark.asyncio
async def test_authenticate_user_invalid_password(mock_user):
    user = mock_user
    session = AsyncMock(spec=AsyncSession)
    with patch(
        "src.app.services.auth.get_user_by_name",
        new_callable=AsyncMock,
        return_value=user,
    ), patch("src.app.services.auth.verify_password", return_value=False):
        with pytest.raises(HTTPException) as exc:
            await authenticate_user(session, "testuser", "wrong_password")
        assert exc.value.status_code == 401
        assert exc.value.detail == "Invalid email or password"
