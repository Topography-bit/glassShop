import string
import secrets
from datetime import datetime, timedelta, timezone
from passlib.context import CryptContext
from jose import jwt
from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType

from app.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ACCESS_TOKEN_EXPIRE = 30
REFRESH_TOKEN_EXPIRE = 30
SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.ALGORITHM


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    return pwd_context.verify(password, hashed_password)


def create_access_token(data: dict) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE)
    to_encode = data.copy()
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(claims=to_encode, key=SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: dict) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE)
    to_encode = data.copy()
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(claims=to_encode, key=SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def set_cookies(response, user_id: int) -> None:
    """Функция установки access и refresh token\'а"""
    access_token = create_access_token({"sub": str(user_id)})
    refresh_token = create_refresh_token({"sub": str(user_id)})

    response.set_cookie(key="access", value=access_token, httponly=True, max_age=ACCESS_TOKEN_EXPIRE*60)
    response.set_cookie(key="refresh", value=refresh_token, httponly=True, max_age=REFRESH_TOKEN_EXPIRE*24*60*60)


def generate_code():
    return "".join(secrets.choice(string.digits) for _ in range(6))

conf = ConnectionConfig(
    MAIL_SERVER=settings.SMTP_HOST,
    MAIL_PORT=settings.SMTP_PORT,
    MAIL_USERNAME=settings.SMTP_USER,
    MAIL_PASSWORD=settings.SMTP_PASSWORD,
    MAIL_FROM=settings.SMTP_FROM,
    MAIL_STARTTLS=settings.SMTP_STARTTLS,
    MAIL_SSL_TLS=settings.SMTP_SSL_TLS,
    USE_CREDENTIALS=settings.USE_CREDENTIALS,
    VALIDATE_CERTS=settings.VALIDATE_CERTS
)

async def send_verify_email(email_to: str, code: str) -> None:
    """Функция отправки письма"""

    html = f"""
    <div style="
        font-family: Arial, sans-serif;
        background-color: #f5f7fa;
        padding: 30px;
    ">
        <div style="
            max-width: 420px;
            margin: 0 auto;
            background-color: #ffffff;
            border-radius: 12px;
            padding: 30px;
            text-align: center;
            box-shadow: 0 8px 24px rgba(0,0,0,0.08);
        ">
            <h1 style="
                margin-top: 0;
                color: #222;
                font-size: 24px;
            ">
                Добро пожаловать в <span style="color:#4a90e2;">Glass Shop</span> 👋
            </h1>

            <p style="
                color: #555;
                font-size: 16px;
                margin-bottom: 25px;
            ">
                Используйте код ниже для подтверждения:
            </p>

            <div style="
                font-size: 28px;
                font-weight: bold;
                letter-spacing: 6px;
                color: #4a90e2;
                margin-bottom: 25px;
            ">
                {code}
            </div>

            <p style="
                color: #888;
                font-size: 14px;
                margin-bottom: 0;
            ">
                Код действует <b>10 минут</b>.<br>
                Если вы не запрашивали код — просто проигнорируйте это письмо.
            </p>
        </div>
    </div>
    """
        
    message = MessageSchema(
        subject="Подтверждение регистрации Glass Shop",
        recipients=[email_to],
        body=html,
        subtype=MessageType.html
    )

    fm = FastMail(conf)

    await fm.send_message(message)