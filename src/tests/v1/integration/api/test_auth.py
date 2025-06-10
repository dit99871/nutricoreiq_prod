import pytest
from fastapi.testclient import TestClient


@pytest.mark.asyncio
async def test_register_success(client: TestClient):
    """Тестирует успешную регистрацию пользователя."""
    user_data = {
        "username": "newuser",
        "email": "newuser@example.com",
        "password": "password123",
    }
    response = client.post("/register", json=user_data)
    assert response.status_code == 201
    assert response.json() == user_data


@pytest.mark.asyncio
async def test_register_duplicate_email(client: TestClient, clean_db):
    """Тестирует ошибку при дубликате email."""
    user_data = {
        "username": "newuser",
        "email": "newuser@example.com",
        "password": "password123",
    }
    response1 = client.post("/register", json=user_data)
    assert response1.status_code == 201
    response2 = client.post("/register", json=user_data)
    assert response2.status_code == 400
    assert response2.json()["detail"] == "Email already registered"


@pytest.mark.asyncio
async def test_login_success(client: TestClient, clean_db):
    """Тестирует успешный логин."""
    user_data = {
        "username": "newuser",
        "email": "newuser@example.com",
        "password": "password123",
    }
    client.post("/register", json=user_data)
    response = client.post(
        "/login",
        data={"username": "newuser", "password": "password123"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert response.status_code == 200
    assert "access_token" in response.json()
    assert "refresh_token" in response.json()
    assert response.cookies.get("access_token") is not None
    assert response.cookies.get("refresh_token") is not None


@pytest.mark.asyncio
async def test_login_invalid_credentials(client: TestClient, clean_db):
    """Тестирует ошибку при неверных учетных данных."""
    user_data = {
        "username": "newuser",
        "email": "newuser@example.com",
        "password": "password123",
    }
    client.post("/register", json=user_data)
    response = client.post(
        "/login",
        data={"username": "newuser", "password": "wrongpassword"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert response.status_code == 401
    assert "Invalid credentials" in response.json()["detail"]


@pytest.mark.asyncio
async def test_logout_success(client: TestClient, clean_db, mock_redis):
    """Тестирует успешный выход."""
    user_data = {
        "username": "newuser",
        "email": "newuser@example.com",
        "password": "password123",
    }
    client.post("/register", json=user_data)
    login_response = client.post(
        "/login",
        data={"username": "newuser", "password": "password123"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    access_token = login_response.cookies.get("access_token")
    refresh_token = login_response.cookies.get("refresh_token")
    response = client.get(
        "/logout",
        cookies={"access_token": access_token, "refresh_token": refresh_token},
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/"
    # Проверяем удаление куков через заголовки
    set_cookie_headers = response.headers.getlist("Set-Cookie")
    access_token_deleted = any(
        "access_token=" in header.lower() and "max-age=0" in header.lower()
        for header in set_cookie_headers
    )
    refresh_token_deleted = any(
        "refresh_token=" in header.lower() and "max-age=0" in header.lower()
        for header in set_cookie_headers
    )
    assert (
        access_token_deleted
    ), f"access_token not deleted, headers: {set_cookie_headers}"
    assert (
        refresh_token_deleted
    ), f"refresh_token not deleted, headers: {set_cookie_headers}"


@pytest.mark.asyncio
async def test_logout_no_refresh_token(client: TestClient, clean_db):
    """Тестирует ошибку при отсутствии refresh-токена."""
    user_data = {
        "username": "newuser",
        "email": "newuser@example.com",
        "password": "password123",
    }
    client.post("/register", json=user_data)
    login_response = client.post(
        "/login",
        data={"username": "newuser", "password": "password123"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    access_token = login_response.cookies.get("access_token")
    response = client.get("/logout", cookies={"access_token": access_token})
    assert response.status_code == 401
    assert response.json()["detail"] == "No refresh token in cookies"


@pytest.mark.asyncio
async def test_refresh_success(client: TestClient, clean_db, mock_redis):
    """Тестирует успешное обновление токенов."""
    user_data = {
        "username": "newuser",
        "email": "newuser@example.com",
        "password": "password123",
    }
    client.post("/register", json=user_data)
    login_response = client.post(
        "/login",
        data={"username": "newuser", "password": "password123"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    refresh_token = login_response.cookies.get("refresh_token")
    response = client.post("/refresh", cookies={"refresh_token": refresh_token})
    assert response.status_code == 200
    assert "access_token" in response.json()
    assert "refresh_token" in response.json()
    assert response.cookies.get("access_token") is not None
    assert response.cookies.get("refresh_token") is not None


@pytest.mark.asyncio
async def test_refresh_no_token(client: TestClient, clean_db, mock_redis):
    """Тестирует ошибку при отсутствии refresh-токена."""
    response = client.post("/refresh")
    assert response.status_code == 401
    assert response.json()["detail"] == "No refresh token found in cookies"


@pytest.mark.asyncio
async def test_change_password_success(client: TestClient, clean_db):
    """Тестирует успешную смену пароля."""
    user_data = {
        "username": "newuser",
        "email": "newuser@example.com",
        "password": "password123",
    }
    client.post("/register", json=user_data)
    login_response = client.post(
        "/login",
        data={"username": "newuser", "password": "password123"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    access_token = login_response.cookies.get("access_token")
    response = client.post("/password/change", cookies={"access_token": access_token})
    assert response.status_code == 200
    assert "access_token" in response.json()
    assert "refresh_token" in response.json()
