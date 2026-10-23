from functools import lru_cache
from pathlib import Path
from pydantic import AliasChoices, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FRONTEND_DIR = PROJECT_ROOT / "frontend"
DATA_DIR = PROJECT_ROOT / "data"


class Settings(BaseSettings):
    app_name: str = "Lotus Hotel AI"
    secret_key: str = "development-only-secret"
    database_url: str = f"sqlite:///{(DATA_DIR / 'hotel.db').as_posix()}"
    gemini_api_key: SecretStr = Field(default=SecretStr(""), validation_alias=AliasChoices("GEMINI_API_KEY", "GOOGLE_API_KEY"))
    gemini_model: str = Field(default="gemini-3.5-flash-lite", pattern=r"^gemini-[A-Za-z0-9._-]+$")
    gemini_timeout_seconds: float = Field(default=60, gt=0, le=180)
    gemini_max_output_tokens: int = Field(default=2048, ge=256, le=8192)
    access_token_expire_minutes: int = 480
    model_config = SettingsConfigDict(env_file=PROJECT_ROOT / ".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
