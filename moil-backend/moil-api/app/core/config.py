from pydantic_settings import BaseSettings, SettingsConfigDict
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    DATABASE_URL: str = "sqlite:///./moil.db"
    REDIS_URL: str = "redis://localhost:6379/0"
    SECRET_KEY: str = "dev-only-secret-change-me-dev-only-secret"
    ACCESS_TOKEN_MINUTES: int = 15
    REFRESH_TOKEN_DAYS: int = 7
    CORS_ORIGINS: str = "http://localhost:5173"
    MAX_UPLOAD_MB: int = 25
    MAX_FAILED_LOGINS: int = 5
    LOCKOUT_MINUTES: int = 15
    AUTO_CREATE_TABLES: bool = True  # True: the API creates missing tables itself (local SQLite). False: tables come only from Alembic migrations (deployment).
settings = Settings()
