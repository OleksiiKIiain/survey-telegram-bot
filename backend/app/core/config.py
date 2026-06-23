from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Survey Bot API"
    api_v1_prefix: str = "/api/v1"
    database_url: str = "postgresql+psycopg://survey_user:survey_password@localhost:5432/survey_bot"
    secret_key: str = "dev-secret-key"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 720
    backend_cors_origins: str = Field(default="http://localhost:5173,http://127.0.0.1:5173")

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.backend_cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
