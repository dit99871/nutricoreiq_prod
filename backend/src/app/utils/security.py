from passlib.context import CryptContext

# Создаем контекст для хэширования паролей
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_password_hash(password: str) -> str:
    """
    Хэширует пароль с использованием алгоритма bcrypt.

    :param password: Пароль в виде строки.
    :return: Хэшированный пароль.
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Проверяет, соответствует ли пароль его хэшу.

    :param plain_password: Пароль в виде строки.
    :param hashed_password: Хэшированный пароль.
    :return: True, если пароль верный, иначе False.
    """
    return pwd_context.verify(plain_password, hashed_password)
