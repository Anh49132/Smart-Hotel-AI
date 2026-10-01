from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FRONTEND_DIR = PROJECT_ROOT / "frontend"
DATA_DIR = PROJECT_ROOT / "data"


class Settings(BaseSettings):
    app_name: str = "Lotus Hotel AI"
    secret_key: str = "development-only-secret"
    database_url: str = f"sqlite:///{(DATA_DIR / 'hotel.db').as_posix()}"
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5"
    access_token_expire_minutes: int = 480
    model_config = SettingsConfigDict(env_file=PROJECT_ROOT / ".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
