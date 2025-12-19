from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    """Хэширует пароль пользователя с помощью bcrypt.
    """

    return pwd_context.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    """Проверяет соответствует ли введенный пароль с тем, который в БД.
    """

    return pwd_context.verify(password, hashed_password)