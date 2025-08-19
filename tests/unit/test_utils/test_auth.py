import pytest

from src.app.core.utils import auth


def test_get_password_hash_returns_bytes():
    """
    Test that get_password_hash returns a bytes object.
    """
    password = "test_password"
    hashed_password = auth.get_password_hash(password)
    assert isinstance(hashed_password, bytes)
    assert len(hashed_password) > 0  # гарантирует, что хэш не пустой


def test_get_password_hash_unique_hashes():
    """
    Test that get_password_hash generates different
    hashes for the same password due to random salt.
    """
    password = "test_password"
    hash1 = auth.get_password_hash(password)
    hash2 = auth.get_password_hash(password)
    assert hash1 != hash2  # разные salt генерируют разные хэши


def test_get_password_hash_empty_password():
    """
    Test get_password_hash with an empty password.
    """
    hashed_password = auth.get_password_hash("")
    assert isinstance(hashed_password, bytes)
    assert auth.verify_password("", hashed_password)  # проверка на пустое значение


def test_verify_password_correct():
    """
    Test verify_password with correct password.
    """
    password = "test_password"
    hashed_password = auth.get_password_hash(password)
    assert auth.verify_password(password, hashed_password) is True


def test_verify_password_incorrect():
    """
    Test verify_password with incorrect password.
    """
    password = "test_password"
    hashed_password = auth.get_password_hash(password)
    assert auth.verify_password("wrong_password", hashed_password) is False


def test_verify_password_invalid_hashed_password():
    """
    Test verify_password with invalid hashed password.
    """
    with pytest.raises(ValueError, match="Invalid salt"):
        auth.verify_password("test_password", b"invalid_hash")


def test_verify_password_empty_hashed_password():
    """
    Test verify_password with empty hashed password.
    """
    with pytest.raises(ValueError, match="Invalid salt"):
        auth.verify_password("test_password", b"")


def test_verify_password_none_hashed_password():
    """
    Test verify_password with None as hashed password.
    """
    with pytest.raises(TypeError):
        auth.verify_password("test_password", None)


def test_decode_jwt_returns_none():
    """
    Test decode_jwt with None as token.
    """
    assert auth.decode_jwt(None) is None
