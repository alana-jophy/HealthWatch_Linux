import json
from typing import List, Union
from pydantic import AliasChoices, AnyHttpUrl, Field, field_validator
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

    # Administrator User Configuration (Configurable via .env)
    ADMIN_EMAIL: str = Field(
        default="admin@healthwatch.org",
        validation_alias=AliasChoices("ADMIN_EMAIL", "FIRST_SUPERUSER_EMAIL"),
    )
    ADMIN_PASSWORD: str = Field(
        default="Admin@HealthWatch2026",
        validation_alias=AliasChoices("ADMIN_PASSWORD", "FIRST_SUPERUSER_PASSWORD"),
    )
    ADMIN_NAME: str = Field(
        default="System Administrator",
        validation_alias=AliasChoices("ADMIN_NAME", "FIRST_SUPERUSER_NAME"),
    )

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
        if isinstance(v, str):
            v_clean = v.strip()
            if v_clean.startswith("[") and v_clean.endswith("]"):
                try:
                    parsed = json.loads(v_clean)
                    if isinstance(parsed, list):
                        return [str(item).strip() for item in parsed if str(item).strip()]
                except Exception:
                    # Strip outer brackets and split by comma if not valid JSON quotes
                    v_clean = v_clean[1:-1]
            origins = [i.strip().strip("'\"") for i in v_clean.split(",") if i.strip().strip("'\"")]
            if origins:
                return origins
        elif isinstance(v, list):
            return [str(i).strip() for i in v if str(i).strip()]
        return ["http://localhost:5173", "http://127.0.0.1:5173"]

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def assemble_db_connection(cls, v: str, info) -> str:
        if isinstance(v, str) and v.strip():
            url = v.strip()
            if url.startswith("postgresql://"):
                try:
                    import psycopg  # noqa: F401
                except ImportError:
                    try:
                        import psycopg2  # noqa: F401
                        url = "postgresql+psycopg2://" + url[len("postgresql://"):]
                    except ImportError:
                        pass
            return url
        values = info.data
        user = values.get("POSTGRES_USER", "healthwatch_user")
        password = values.get("POSTGRES_PASSWORD", "healthwatch_secure_password_123")
        server = values.get("POSTGRES_SERVER", "localhost")
        port = values.get("POSTGRES_PORT", 5432)
        db = values.get("POSTGRES_DB", "healthwatch_db")
        url = f"postgresql://{user}:{password}@{server}:{port}/{db}"
        try:
            import psycopg  # noqa: F401
        except ImportError:
            try:
                import psycopg2  # noqa: F401
                url = f"postgresql+psycopg2://{user}:{password}@{server}:{port}/{db}"
            except ImportError:
                pass
        return url

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="allow",
    )


settings = Settings()
