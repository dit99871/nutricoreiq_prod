import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from models import DeletedUser, User
from app.crud.user import create_user, delete_user, get_user_by_email, update_user
from schemas import UserCreate, UserUpdate
from core.utils.security import get_password_hash, verify_password


@pytest.mark.asyncio
async def test_get_user_by_email_found():
    """
    Тест для случая, когда пользователь найден по email.
    """
    # Создаем мок для AsyncSession
    mock_session = AsyncMock(spec=AsyncSession)

    # Создаем мок для результата запроса
    mock_user = User(
        id=1,
        username="testuser",
        email="test@example.com",
        hashed_password=get_password_hash("password123"),
        gender="male",
        age=25,
        weight=70.5,
        is_active=True,
        is_admin=False,
    )
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = mock_user

    # Мокируем метод execute
    mock_session.execute.return_value = mock_result

    # Вызываем тестируемую функцию
    result = await get_user_by_email(mock_session, "test@example.com")

    # Проверяем результат
    assert result == mock_user
    assert verify_password(
        "password123", result.hashed_password
    )  # Проверка хэша пароля
    mock_session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_get_user_by_email_not_found():
    """
    Тест для случая, когда пользователь не найден по email.
    """
    # Создаем мок для AsyncSession
    mock_session = AsyncMock(spec=AsyncSession)

    # Мокируем пустой результат
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = None

    # Мокируем метод execute
    mock_session.execute.return_value = mock_result

    # Вызываем тестируемую функцию
    result = await get_user_by_email(mock_session, "test@example.com")

    # Проверяем результат
    assert result is None
    mock_session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_create_user_success():
    """
    Тест для успешного создания пользователя.
    """
    # Создаем мок для AsyncSession
    mock_session = AsyncMock(spec=AsyncSession)

    # Создаем тестовые данные для UserCreate
    user_data = UserCreate(
        username="testuser",
        email="test@example.com",
        password="password123",
        gender="male",
        age=25,
        weight=70.5,
    )

    # Мокируем методы commit и refresh
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock()

    # Вызываем тестируемую функцию
    result = await create_user(mock_session, user_data)

    # Проверяем результат
    assert result is not None
    assert result.username == user_data.username
    assert result.email == user_data.email
    assert verify_password(
        user_data.password, result.hashed_password
    )  # Проверка хэша пароля
    assert result.gender == user_data.gender
    assert result.age == user_data.age
    assert result.weight == user_data.weight

    # Проверяем, что методы были вызваны
    mock_session.add.assert_called_once()
    mock_session.commit.assert_called_once()
    mock_session.refresh.assert_called_once()

    # Проверяем логирование
    with patch("logging.info") as mock_logging_info:
        await create_user(mock_session, user_data)
        mock_logging_info.assert_called_once_with(
            f"User created with email: {user_data.email}"
        )


@pytest.mark.asyncio
async def test_create_user_database_error():
    """
    Тест для случая, когда возникает ошибка базы данных.
    """
    # Создаем мок для AsyncSession
    mock_session = AsyncMock(spec=AsyncSession)

    # Создаем тестовые данные для UserCreate
    user_data = UserCreate(
        username="testuser",
        email="test@example.com",
        password="password123",
        gender="male",
        age=25,
        weight=70.5,
    )

    # Мокируем ошибку базы данных
    mock_session.commit.side_effect = SQLAlchemyError("Database error")

    # Вызываем тестируемую функцию
    result = await create_user(mock_session, user_data)

    # Проверяем результат
    assert result is None

    # Проверяем, что rollback был вызван
    mock_session.rollback.assert_called_once()

    # Проверяем логирование
    with patch("logging.error") as mock_logging_error:
        await create_user(mock_session, user_data)
        mock_logging_error.assert_called_once_with(
            f"Database error creating user with email {user_data.email}: Database error"
        )


@pytest.mark.asyncio
async def test_create_user_unexpected_error():
    """
    Тест для случая, когда возникает неожиданная ошибка.
    """
    # Создаем мок для AsyncSession
    mock_session = AsyncMock(spec=AsyncSession)

    # Создаем тестовые данные для UserCreate
    user_data = UserCreate(
        username="testuser",
        email="test@example.com",
        password="password123",
        gender="male",
        age=25,
        weight=70.5,
    )

    # Мокируем неожиданную ошибку
    mock_session.commit.side_effect = Exception("Unexpected error")

    # Вызываем тестируемую функцию
    result = await create_user(mock_session, user_data)

    # Проверяем результат
    assert result is None

    # Проверяем, что rollback был вызван
    mock_session.rollback.assert_called_once()

    # Проверяем логирование
    with patch("logging.exception") as mock_logging_exception:
        await create_user(mock_session, user_data)
        mock_logging_exception.assert_called_once_with(
            f"Unexpected error creating user with email {user_data.email}: Unexpected error"
        )


@pytest.mark.asyncio
async def test_update_user_success():
    """
    Тест для успешного обновления данных пользователя.
    """
    # Создаем мок для AsyncSession
    mock_session = AsyncMock(spec=AsyncSession)

    # Создаем мок для существующего пользователя
    mock_user = User(
        id=1,
        username="testuser",
        email="test@example.com",
        hashed_password="hashed_password",
        gender="male",
        age=25,
        weight=70.5,
        is_active=True,
        is_admin=False,
    )

    # Мокируем get_user_by_email
    mock_get_user_by_email = AsyncMock(return_value=mock_user)
    with patch("app.crud.user.get_user_by_email", mock_get_user_by_email):
        # Создаем тестовые данные для UserUpdate
        user_update_data = UserUpdate(
            username="updateduser",
            age=30,
            weight=75.0,
        )

        # Мокируем методы commit и refresh
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        # Вызываем тестируемую функцию
        result = await update_user(mock_session, "test@example.com", user_update_data)

        # Проверяем результат
        assert result is not None
        assert result.username == user_update_data.username
        assert result.age == user_update_data.age
        assert result.weight == user_update_data.weight

        # Проверяем, что методы были вызваны
        mock_session.commit.assert_called_once()
        mock_session.refresh.assert_called_once()

        # Проверяем логирование
        with patch("logging.info") as mock_logging_info:
            await update_user(mock_session, "test@example.com", user_update_data)
            mock_logging_info.assert_called_once_with(
                "User updated with email: test@example.com"
            )


@pytest.mark.asyncio
async def test_update_user_not_found():
    """
    Тест для случая, когда пользователь не найден.
    """
    # Создаем мок для AsyncSession
    mock_session = AsyncMock(spec=AsyncSession)

    # Мокируем get_user_by_email, чтобы вернуть None
    mock_get_user_by_email = AsyncMock(return_value=None)
    with patch("app.crud.user.get_user_by_email", mock_get_user_by_email):
        # Создаем тестовые данные для UserUpdate
        user_update_data = UserUpdate(
            username="updateduser",
            age=30,
            weight=75.0,
        )

        # Вызываем тестируемую функцию
        result = await update_user(mock_session, "test@example.com", user_update_data)

        # Проверяем результат
        assert result is None

        # Проверяем логирование
        with patch("logging.warning") as mock_logging_warning:
            await update_user(mock_session, "test@example.com", user_update_data)
            mock_logging_warning.assert_called_once_with(
                "User not found for update with email: test@example.com"
            )


@pytest.mark.asyncio
async def test_update_user_database_error():
    """
    Тест для случая, когда возникает ошибка базы данных.
    """
    # Создаем мок для AsyncSession
    mock_session = AsyncMock(spec=AsyncSession)

    # Создаем мок для существующего пользователя
    mock_user = User(
        id=1,
        username="testuser",
        email="test@example.com",
        hashed_password="hashed_password",
        gender="male",
        age=25,
        weight=70.5,
        is_active=True,
        is_admin=False,
    )

    # Мокируем get_user_by_email
    mock_get_user_by_email = AsyncMock(return_value=mock_user)
    with patch("app.crud.user.get_user_by_email", mock_get_user_by_email):
        # Создаем тестовые данные для UserUpdate
        user_update_data = UserUpdate(
            username="updateduser",
            age=30,
            weight=75.0,
        )

        # Мокируем ошибку базы данных
        mock_session.commit.side_effect = SQLAlchemyError("Database error")

        # Вызываем тестируемую функцию
        result = await update_user(mock_session, "test@example.com", user_update_data)

        # Проверяем результат
        assert result is None

        # Проверяем, что rollback был вызван
        mock_session.rollback.assert_called_once()

        # Проверяем логирование
        with patch("logging.error") as mock_logging_error:
            await update_user(mock_session, "test@example.com", user_update_data)
            mock_logging_error.assert_called_once_with(
                "Database error updating user with email test@example.com: Database error"
            )


@pytest.mark.asyncio
async def test_update_user_unexpected_error():
    """
    Тест для случая, когда возникает неожиданная ошибка.
    """
    # Создаем мок для AsyncSession
    mock_session = AsyncMock(spec=AsyncSession)

    # Создаем мок для существующего пользователя
    mock_user = User(
        id=1,
        username="testuser",
        email="test@example.com",
        hashed_password="hashed_password",
        gender="male",
        age=25,
        weight=70.5,
        is_active=True,
        is_admin=False,
    )

    # Мокируем get_user_by_email
    mock_get_user_by_email = AsyncMock(return_value=mock_user)
    with patch("app.crud.user.get_user_by_email", mock_get_user_by_email):
        # Создаем тестовые данные для UserUpdate
        user_update_data = UserUpdate(
            username="updateduser",
            age=30,
            weight=75.0,
        )

        # Мокируем неожиданную ошибку
        mock_session.commit.side_effect = Exception("Unexpected error")

        # Вызываем тестируемую функцию
        result = await update_user(mock_session, "test@example.com", user_update_data)

        # Проверяем результат
        assert result is None

        # Проверяем, что rollback был вызван
        mock_session.rollback.assert_called_once()

        # Проверяем логирование
        with patch("logging.exception") as mock_logging_exception:
            await update_user(mock_session, "test@example.com", user_update_data)
            mock_logging_exception.assert_called_once_with(
                "Unexpected error updating user with email test@example.com: Unexpected error"
            )


@pytest.mark.asyncio
async def test_delete_user_success():
    """
    Тест для успешного удаления пользователя.
    """
    # Создаем мок для AsyncSession
    mock_session = AsyncMock(spec=AsyncSession)

    # Создаем мок для существующего пользователя
    mock_user = User(
        id=1,
        username="testuser",
        email="test@example.com",
        hashed_password="hashed_password",
        gender="male",
        age=25,
        weight=70.5,
        is_active=True,
        is_admin=False,
    )

    # Мокируем get_user_by_email
    mock_get_user_by_email = AsyncMock(return_value=mock_user)
    with patch("app.crud.user.get_user_by_email", mock_get_user_by_email):
        # Мокируем методы commit и refresh
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        # Вызываем тестируемую функцию
        result = await delete_user(mock_session, "test@example.com")

        # Проверяем результат
        assert result is not None
        assert isinstance(result, DeletedUser)
        assert result.email == mock_user.email
        assert result.username == mock_user.username

        # Проверяем, что методы были вызваны
        mock_session.add.assert_called_once()
        mock_session.delete.assert_called_once_with(mock_user)
        mock_session.commit.assert_called()
        mock_session.refresh.assert_called_once()

        # Проверяем логирование
        with patch("logging.info") as mock_logging_info:
            await delete_user(mock_session, "test@example.com")
            mock_logging_info.assert_called_once_with(
                "User deleted with email: test@example.com"
            )


@pytest.mark.asyncio
async def test_delete_user_not_found():
    """
    Тест для случая, когда пользователь не найден.
    """
    # Создаем мок для AsyncSession
    mock_session = AsyncMock(spec=AsyncSession)

    # Мокируем get_user_by_email, чтобы вернуть None
    mock_get_user_by_email = AsyncMock(return_value=None)
    with patch("app.crud.user.get_user_by_email", mock_get_user_by_email):
        # Вызываем тестируемую функцию
        result = await delete_user(mock_session, "test@example.com")

        # Проверяем результат
        assert result is None

        # Проверяем логирование
        with patch("logging.warning") as mock_logging_warning:
            await delete_user(mock_session, "test@example.com")
            mock_logging_warning.assert_called_once_with(
                "User not found for deletion with email: test@example.com"
            )


@pytest.mark.asyncio
async def test_delete_user_database_error():
    """
    Тест для случая, когда возникает ошибка базы данных.
    """
    # Создаем мок для AsyncSession
    mock_session = AsyncMock(spec=AsyncSession)

    # Создаем мок для существующего пользователя
    mock_user = User(
        id=1,
        username="testuser",
        email="test@example.com",
        hashed_password="hashed_password",
        gender="male",
        age=25,
        weight=70.5,
        is_active=True,
        is_admin=False,
    )

    # Мокируем get_user_by_email
    mock_get_user_by_email = AsyncMock(return_value=mock_user)
    with patch("app.crud.user.get_user_by_email", mock_get_user_by_email):
        # Мокируем ошибку базы данных
        mock_session.commit.side_effect = SQLAlchemyError("Database error")

        # Вызываем тестируемую функцию
        result = await delete_user(mock_session, "test@example.com")

        # Проверяем результат
        assert result is None

        # Проверяем, что rollback был вызван
        mock_session.rollback.assert_called_once()

        # Проверяем логирование
        with patch("logging.error") as mock_logging_error:
            await delete_user(mock_session, "test@example.com")
            mock_logging_error.assert_called_once_with(
                "Database error deleting user with email test@example.com: Database error"
            )


@pytest.mark.asyncio
async def test_delete_user_unexpected_error():
    """
    Тест для случая, когда возникает неожиданная ошибка.
    """
    # Создаем мок для AsyncSession
    mock_session = AsyncMock(spec=AsyncSession)

    # Создаем мок для существующего пользователя
    mock_user = User(
        id=1,
        username="testuser",
        email="test@example.com",
        hashed_password="hashed_password",
        gender="male",
        age=25,
        weight=70.5,
        is_active=True,
        is_admin=False,
    )

    # Мокируем get_user_by_email
    mock_get_user_by_email = AsyncMock(return_value=mock_user)
    with patch("app.crud.user.get_user_by_email", mock_get_user_by_email):
        # Мокируем неожиданную ошибку
        mock_session.commit.side_effect = Exception("Unexpected error")

        # Вызываем тестируемую функцию
        result = await delete_user(mock_session, "test@example.com")

        # Проверяем результат
        assert result is None

        # Проверяем, что rollback был вызван
        mock_session.rollback.assert_called_once()

        # Проверяем логирование
        with patch("logging.exception") as mock_logging_exception:
            await delete_user(mock_session, "test@example.com")
            mock_logging_exception.assert_called_once_with(
                "Unexpected error deleting user with email test@example.com: Unexpected error"
            )
