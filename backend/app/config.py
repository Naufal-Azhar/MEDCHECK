"""Application settings loaded from the project environment."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    app_env: str = "development"
    log_level: str = "INFO"
    database_url: str = "postgresql+psycopg://forgehacks:forgehacks_dev@localhost:5433/forgehacks"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)
