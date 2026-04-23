"""
Тесты для сервиса отправки email.
Покрывает: send_email, send_welcome_email.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.app.core.schemas.user import UserPublic


@pytest.fixture
def user_public():
    """Фикстура публичного пользователя."""
    return UserPublic(
        id=1,
        uid="user-uid-123",
        username="testuser",
        email="test@example.com",
    )


@pytest.fixture
def mock_settings():
    """Мок настроек почтового сервиса."""
    settings = MagicMock()
    settings.mail.host = "smtp.example.com"
    settings.mail.port = 587
    settings.mail.use_tls = False
    settings.mail.username = "sender@example.com"
    settings.mail.password = "secret"
    settings.mail.button_link = "http://example.com/login"
    settings.mail.unsubscribe_link = "http://example.com/unsub"
    return settings


# ─── send_email ───────────────────────────────────────────────────────────────


class TestSendEmail:
    """Тесты для функции send_email."""

    @pytest.mark.asyncio
    async def test_send_email_success(self, mock_settings):
        """Успешная отправка письма вызывает aiosmtplib.send."""
        with patch("src.app.core.services.email.settings", mock_settings):
            with patch("src.app.core.services.email.aiosmtplib.send", new_callable=AsyncMock) as mock_send:
                with patch("src.app.core.services.email.env") as mock_env:
                    mock_template = MagicMock()
                    mock_template.render.return_value = "<h1>Hello</h1>"
                    mock_env.get_template.return_value = mock_template

                    from src.app.core.services.email import send_email

                    await send_email(
                        recipient="user@example.com",
                        sender="sender@example.com",
                        subject="Test Subject",
                        template="emails/welcome_email.html",
                        context={"username": "testuser"},
                    )

                mock_send.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_email_calls_get_template(self, mock_settings):
        """Вызывает get_template с правильным именем шаблона."""
        with patch("src.app.core.services.email.settings", mock_settings):
            with patch("src.app.core.services.email.aiosmtplib.send", new_callable=AsyncMock):
                with patch("src.app.core.services.email.env") as mock_env:
                    mock_template = MagicMock()
                    mock_template.render.return_value = "<h1>Hello</h1>"
                    mock_env.get_template.return_value = mock_template

                    from src.app.core.services.email import send_email

                    await send_email(
                        recipient="user@example.com",
                        sender="sender@example.com",
                        subject="Test",
                        template="emails/welcome_email.html",
                        context={},
                    )

                mock_env.get_template.assert_called_once_with("emails/welcome_email.html")

    @pytest.mark.asyncio
    async def test_send_email_renders_context(self, mock_settings):
        """Передаёт контекст в шаблон."""
        with patch("src.app.core.services.email.settings", mock_settings):
            with patch("src.app.core.services.email.aiosmtplib.send", new_callable=AsyncMock):
                with patch("src.app.core.services.email.env") as mock_env:
                    mock_template = MagicMock()
                    mock_template.render.return_value = "<p>Welcome, testuser!</p>"
                    mock_env.get_template.return_value = mock_template

                    from src.app.core.services.email import send_email

                    context = {"username": "testuser", "link": "http://example.com"}
                    await send_email(
                        recipient="user@example.com",
                        sender="sender@example.com",
                        subject="Welcome",
                        template="emails/welcome_email.html",
                        context=context,
                    )

                mock_template.render.assert_called_once_with(**context)

    @pytest.mark.asyncio
    async def test_send_email_smtp_exception_raises(self, mock_settings):
        """При SMTPException поднимает общий Exception с маскированным email."""
        from aiosmtplib.errors import SMTPException

        with patch("src.app.core.services.email.settings", mock_settings):
            with patch("src.app.core.services.email.aiosmtplib.send", new_callable=AsyncMock) as mock_send:
                mock_send.side_effect = SMTPException("Connection refused")
                with patch("src.app.core.services.email.env") as mock_env:
                    mock_template = MagicMock()
                    mock_template.render.return_value = "<h1>Hello</h1>"
                    mock_env.get_template.return_value = mock_template

                    from src.app.core.services.email import send_email

                    with pytest.raises(Exception) as exc_info:
                        await send_email(
                            recipient="user@example.com",
                            sender="sender@example.com",
                            subject="Test",
                            template="emails/test.html",
                            context={},
                        )

                assert "u***r@example.com" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_send_email_no_auth_if_missing_credentials(self):
        """Если username/password не заданы, auth-поля не передаются."""
        settings = MagicMock()
        settings.mail.host = "smtp.example.com"
        settings.mail.port = 25
        settings.mail.use_tls = None
        settings.mail.username = None
        settings.mail.password = None

        with patch("src.app.core.services.email.settings", settings):
            with patch("src.app.core.services.email.aiosmtplib.send", new_callable=AsyncMock) as mock_send:
                with patch("src.app.core.services.email.env") as mock_env:
                    mock_template = MagicMock()
                    mock_template.render.return_value = "<h1>Hello</h1>"
                    mock_env.get_template.return_value = mock_template

                    from src.app.core.services.email import send_email

                    await send_email(
                        recipient="user@example.com",
                        sender="no-reply@example.com",
                        subject="Test",
                        template="emails/test.html",
                        context={},
                    )

                # проверяем что username/password не переданы
                call_kwargs = mock_send.call_args[1]
                assert "username" not in call_kwargs
                assert "password" not in call_kwargs

    @pytest.mark.asyncio
    async def test_send_email_with_auth_credentials_passed(self, mock_settings):
        """Если username и password заданы, они передаются в send."""
        with patch("src.app.core.services.email.settings", mock_settings):
            with patch("src.app.core.services.email.aiosmtplib.send", new_callable=AsyncMock) as mock_send:
                with patch("src.app.core.services.email.env") as mock_env:
                    mock_template = MagicMock()
                    mock_template.render.return_value = "<h1>Hello</h1>"
                    mock_env.get_template.return_value = mock_template

                    from src.app.core.services.email import send_email

                    await send_email(
                        recipient="user@example.com",
                        sender="sender@example.com",
                        subject="Test",
                        template="emails/test.html",
                        context={},
                    )

                call_kwargs = mock_send.call_args[1]
                assert call_kwargs["username"] == "sender@example.com"
                assert call_kwargs["password"] == "secret"


# ─── send_welcome_email ───────────────────────────────────────────────────────


class TestSendWelcomeEmail:
    """Тесты для send_welcome_email."""

    @pytest.mark.asyncio
    async def test_send_welcome_email_calls_send_email(self, user_public, mock_settings):
        """Вызывает send_email с правильными параметрами."""
        with patch("src.app.core.services.email.settings", mock_settings):
            with patch("src.app.core.services.email.send_email", new_callable=AsyncMock) as mock_send:
                from src.app.core.services.email import send_welcome_email

                await send_welcome_email(user_public)

            mock_send.assert_called_once()
            call_kwargs = mock_send.call_args[1]
            assert call_kwargs["recipient"] == "test@example.com"
            assert "welcome" in call_kwargs["template"].lower()

    @pytest.mark.asyncio
    async def test_send_welcome_email_subject(self, user_public, mock_settings):
        """Проверяет тему письма."""
        with patch("src.app.core.services.email.settings", mock_settings):
            with patch("src.app.core.services.email.send_email", new_callable=AsyncMock) as mock_send:
                from src.app.core.services.email import send_welcome_email

                await send_welcome_email(user_public)

            call_kwargs = mock_send.call_args[1]
            assert "NutricoreIQ" in call_kwargs["subject"]

    @pytest.mark.asyncio
    async def test_send_welcome_email_context_contains_username(self, user_public, mock_settings):
        """Контекст шаблона содержит username пользователя."""
        with patch("src.app.core.services.email.settings", mock_settings):
            with patch("src.app.core.services.email.send_email", new_callable=AsyncMock) as mock_send:
                from src.app.core.services.email import send_welcome_email

                await send_welcome_email(user_public)

            call_kwargs = mock_send.call_args[1]
            assert call_kwargs["context"]["username"] == "testuser"

    @pytest.mark.asyncio
    async def test_send_welcome_email_context_contains_links(self, user_public, mock_settings):
        """Контекст содержит button_link и unsubscribe_link."""
        with patch("src.app.core.services.email.settings", mock_settings):
            with patch("src.app.core.services.email.send_email", new_callable=AsyncMock) as mock_send:
                from src.app.core.services.email import send_welcome_email

                await send_welcome_email(user_public)

            call_kwargs = mock_send.call_args[1]
            assert "button_link" in call_kwargs["context"]
            assert "unsubscribe_link" in call_kwargs["context"]

    @pytest.mark.asyncio
    async def test_send_welcome_email_propagates_exception(self, user_public, mock_settings):
        """Исключение из send_email пробрасывается наверх."""
        with patch("src.app.core.services.email.settings", mock_settings):
            with patch(
                "src.app.core.services.email.send_email",
                new_callable=AsyncMock,
                side_effect=Exception("SMTP down"),
            ):
                from src.app.core.services.email import send_welcome_email

                with pytest.raises(Exception, match="SMTP down"):
                    await send_welcome_email(user_public)