"""
Тесты для info router.
"""

from unittest.mock import MagicMock, patch

import pytest
from fastapi import Request

from src.app.core.schemas.user import UserPublic


@pytest.fixture
def mock_request():
    """Создает мок для Request."""
    request = MagicMock(spec=Request)
    request.state = MagicMock()
    request.state.csp_nonce = "test_nonce"
    return request


@pytest.fixture
def user_public():
    """Валидные данные публичного пользователя."""
    return UserPublic(
        id=1,
        uid="test-uid-123",
        username="testuser",
        email="test@example.com",
    )


# --- get_privacy_info ---


@patch("src.app.routers.info.templates.TemplateResponse")
def test_get_privacy_info_with_user(mock_template_response, mock_request, user_public):
    """Тест получения страницы политики конфиденциальности с авторизованным пользователем."""
    from src.app.routers.info import get_privacy_info

    mock_template_response.return_value = MagicMock()

    result = get_privacy_info(mock_request, user_public)

    mock_template_response.assert_called_once()
    call_kwargs = mock_template_response.call_args[1]
    assert call_kwargs["name"] == "privacy.html"
    assert call_kwargs["request"] == mock_request
    assert call_kwargs["context"]["user"] == user_public
    assert call_kwargs["context"]["csp_nonce"] == "test_nonce"
    assert "current_year" in call_kwargs["context"]


@patch("src.app.routers.info.templates.TemplateResponse")
def test_get_privacy_info_without_user(mock_template_response, mock_request):
    """Тест получения страницы политики конфиденциальности без авторизации."""
    from src.app.routers.info import get_privacy_info

    mock_template_response.return_value = MagicMock()

    result = get_privacy_info(mock_request, None)

    call_kwargs = mock_template_response.call_args[1]
    assert call_kwargs["context"]["user"] is None


# --- get_info_about_project ---


@patch("src.app.routers.info.templates.TemplateResponse")
def test_get_info_about_project_with_user(mock_template_response, mock_request, user_public):
    """Тест получения страницы о проекте с авторизованным пользователем."""
    from src.app.routers.info import get_info_about_project

    mock_template_response.return_value = MagicMock()

    result = get_info_about_project(mock_request, user_public)

    mock_template_response.assert_called_once()
    call_kwargs = mock_template_response.call_args[1]
    assert call_kwargs["name"] == "about.html"
    assert call_kwargs["request"] == mock_request
    assert call_kwargs["context"]["user"] == user_public
    assert call_kwargs["context"]["csp_nonce"] == "test_nonce"
    assert "current_year" in call_kwargs["context"]


@patch("src.app.routers.info.templates.TemplateResponse")
def test_get_info_about_project_without_user(mock_template_response, mock_request):
    """Тест получения страницы о проекте без авторизации."""
    from src.app.routers.info import get_info_about_project

    mock_template_response.return_value = MagicMock()

    result = get_info_about_project(mock_request, None)

    call_kwargs = mock_template_response.call_args[1]
    assert call_kwargs["context"]["user"] is None


# --- start_page ---


@patch("src.app.routers.info.templates.TemplateResponse")
def test_start_page_with_user(mock_template_response, mock_request, user_public):
    """Тест получения главной страницы с авторизованным пользователем."""
    from src.app.routers.info import start_page

    mock_template_response.return_value = MagicMock()

    result = start_page(mock_request, user_public)

    mock_template_response.assert_called_once()
    call_kwargs = mock_template_response.call_args[1]
    assert call_kwargs["name"] == "index.html"
    assert call_kwargs["request"] == mock_request
    assert call_kwargs["context"]["user"] == user_public
    assert call_kwargs["context"]["csp_nonce"] == "test_nonce"
    assert "current_year" in call_kwargs["context"]


@patch("src.app.routers.info.templates.TemplateResponse")
def test_start_page_without_user(mock_template_response, mock_request):
    """Тест получения главной страницы без авторизации."""
    from src.app.routers.info import start_page

    mock_template_response.return_value = MagicMock()

    result = start_page(mock_request, None)

    call_kwargs = mock_template_response.call_args[1]
    assert call_kwargs["context"]["user"] is None


def test_start_page_head():
    """Тест HEAD запроса для главной страницы."""
    from src.app.routers.info import start_page_head
    from fastapi.responses import Response

    result = start_page_head()

    assert isinstance(result, Response)
    assert result.status_code == 200
