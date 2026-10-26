from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://cardify:cardify@localhost:5432/cardify"
    jwt_secret: str = "dev-only-secret-change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60

    # Total risk score at or above which a transaction is flagged.
    flag_threshold: int = 50


@lru_cache
def get_settings() -> Settings:
    return Settings()


def normalize_db_url(url: str) -> str:
    """Render/Neon hand out postgres:// URLs; SQLAlchemy + psycopg 3 needs postgresql+psycopg://."""
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix) :]
    return url
