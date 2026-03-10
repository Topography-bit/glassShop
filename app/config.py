from decimal import Decimal

from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    DB_HOST: str
    DB_PORT: int
    DB_NAME: str
    DB_USER: str
    DB_PASS: str

    SECRET_KEY: str
    ALGORITHM: str

    SMTP_HOST: str
    SMTP_PORT: int
    SMTP_USER: str
    SMTP_PASSWORD: str
    SMTP_FROM: str
    SMTP_STARTTLS: bool = True
    SMTP_SSL_TLS: bool = False
    USE_CREDENTIALS: bool = True
    VALIDATE_CERTS: bool = True

    DELIVERY_ORIGIN_NAME: str = "Майкоп"
    DELIVERY_ORIGIN_LAT: float = 44.6078
    DELIVERY_ORIGIN_LON: float = 40.1058
    DELIVERY_MAX_RADIUS_KM: float = 50.0
    DELIVERY_PRICE_PER_KM: Decimal = Decimal("40.00")
    DELIVERY_MIN_PRICE: Decimal = Decimal("400.00")
    GEOCODER_CONTACT_EMAIL: str | None = None

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()
