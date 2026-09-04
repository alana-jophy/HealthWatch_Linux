import json
from typing import List, Union
from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application Settings powered by Pydantic Settings."""

    # Application Information
    APP_NAME: str = "HealthWatch"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    API_V1_STR: str = "/api/v1"

    # Server Binding
    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000

    # Security & Tokens
    SECRET_KEY: str = "healthwatch_super_secret_development_key_32_characters_long"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day

    # Location Telemetry Sampling Configuration (15 minutes = 900 seconds)
    LOCATION_SAMPLING_INTERVAL_SECONDS: int = 900
    LOCATION_SAMPLING_INTERVAL_MINUTES: int = 15

    # Database Configuration (PostgreSQL + PostGIS)
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "healthwatch_user"
    POSTGRES_PASSWORD: str = "healthwatch_secure_password_123"
    POSTGRES_DB: str = "healthwatch_db"
    DATABASE_URL: str = ""

    # CORS Settings
    BACKEND_CORS_ORIGINS: Union[List[str], str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
    ]

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, str) and v.startswith("["):
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return parsed
            except Exception:
                pass
        elif isinstance(v, list):
            return v
        return ["http://localhost:5173", "http://127.0.0.1:5173"]

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def assemble_db_connection(cls, v: str, info) -> str:
        if isinstance(v, str) and v.strip():
            return v
        values = info.data
        user = values.get("POSTGRES_USER", "healthwatch_user")
        password = values.get("POSTGRES_PASSWORD", "healthwatch_secure_password_123")
        server = values.get("POSTGRES_SERVER", "localhost")
        port = values.get("POSTGRES_PORT", 5432)
        db = values.get("POSTGRES_DB", "healthwatch_db")
        return f"postgresql://{user}:{password}@{server}:{port}/{db}"

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="allow",
    )


settings = Settings()
