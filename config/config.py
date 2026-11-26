# config.py
import os

from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Конфигурация приложения."""

    APP_NAME: str = os.getenv("APP_NAME", "MyApp")
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "production")

    # Database
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: int = int(os.getenv("DB_PORT", 5432))
    DB_NAME: str = os.getenv("DB_NAME", "myapp")
    DB_USER: str = os.getenv("DB_USER", "postgres")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "")
    DB_POOL_MIN: int = int(os.getenv("DB_POOL_MIN", 5))
    DB_POOL_MAX: int = int(os.getenv("DB_POOL_MAX", 10))

    @property
    def DATABASE_URL(self) -> str:
        """URL для подключения к базе данных."""
        return (
            f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    # Server
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", 8000))

    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "change-in-production")


settings = Settings()
