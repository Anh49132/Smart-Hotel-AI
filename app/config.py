from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Lotus Hotel AI"
    secret_key: str = "development-only-secret"
    database_url: str = "sqlite:///./hotel.db"
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5"
    access_token_expire_minutes: int = 480
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

