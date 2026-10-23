from functools import lru_cache
from pathlib import Path
from pydantic import AliasChoices, Field, SecretStr, model_validator
from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FRONTEND_DIR = PROJECT_ROOT / "frontend"
DATA_DIR = PROJECT_ROOT / "data"


class Settings(BaseSettings):
    app_name: str = "Lotus Hotel AI"
    app_env: Literal['development', 'testing', 'production'] = 'development'
    secret_key: str = Field(default="development-only-secret", repr=False)
    auto_create_schema: bool = True
    seed_demo_data: bool = True
    demo_mode: bool = False
    demo_seed_on_start: bool = False
    demo_staff_password: SecretStr = SecretStr('')
    bootstrap_admin_password: SecretStr = SecretStr('')
    database_url: str = f"sqlite:///{(DATA_DIR / 'hotel.db').as_posix()}"
    gemini_api_key: SecretStr = Field(default=SecretStr(""), validation_alias=AliasChoices("GEMINI_API_KEY", "GOOGLE_API_KEY"))
    gemini_model: str = Field(default="gemini-3.5-flash-lite", pattern=r"^gemini-[A-Za-z0-9._-]+$")
    gemini_timeout_seconds: float = Field(default=60, gt=0, le=180)
    gemini_max_output_tokens: int = Field(default=2048, ge=256, le=8192)
    access_token_expire_minutes: int = Field(default=480, ge=5, le=1440)
    model_config = SettingsConfigDict(env_file=PROJECT_ROOT / ".env", extra="ignore")

    @model_validator(mode='after')
    def production_safety(self):
        if self.demo_seed_on_start and (not self.demo_mode or len(self.demo_staff_password.get_secret_value())<12):
            raise ValueError('Explicit DEMO_MODE and a private DEMO_STAFF_PASSWORD (12+ chars) are required to seed a demo')
        if self.app_env == 'production':
            if len(self.secret_key) < 32 or self.secret_key in ('change-this-secret-in-production', 'development-only-secret'):
                raise ValueError('Production requires a random SECRET_KEY of at least 32 characters')
            self.auto_create_schema = False
            self.seed_demo_data = False
        password = self.bootstrap_admin_password.get_secret_value()
        if password and (len(password) < 8 or len(password.encode('utf-8')) > 72 or password == 'Admin@123'):
            raise ValueError('Choose a private bootstrap password, 8 characters minimum and 72 UTF-8 bytes maximum')
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
