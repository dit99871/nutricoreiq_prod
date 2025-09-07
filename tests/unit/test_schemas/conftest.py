import pytest


# Общие фикстуры могут быть здесь
@pytest.fixture
def base_user_data():
    return {"username": "testuser", "email": "test@example.com"}
