"""Application settings and configuration management."""

import json
from pathlib import Path
from typing import List, Union
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    """FridgeMind backend configuration."""

    # API Metadata
    PROJECT_NAME: str = "FridgeMind API"
    VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api"

    # Environment & Host
    ENVIRONMENT: str = "development"
    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000
    LOG_LEVEL: str = "INFO"

    # AI Service Configuration
    GEMINI_API_KEY: str = Field(default="", description="Google Gemini API key")
    GEMINI_MODEL: str = "gemini-2.0-flash"

    # CORS
    CORS_ORIGINS: Union[List[str], str] = [
        "http://localhost:8443",
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:8443",
        "http://127.0.0.1:5173",
    ]

    # File uploads
    MAX_UPLOAD_SIZE_BYTES: int = 10 * 1024 * 1024  # 10 MB
    ALLOWED_IMAGE_TYPES: List[str] = ["image/jpeg", "image/png", "image/webp"]

    # Database
    DATABASE_PATH: Path = BASE_DIR / "app" / "data" / "recipes.db"

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            if v.startswith("[") and v.endswith("]"):
                try:
                    return json.loads(v)
                except Exception:
                    pass
            return [i.strip() for i in v.split(",") if i.strip()]
        return v

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
