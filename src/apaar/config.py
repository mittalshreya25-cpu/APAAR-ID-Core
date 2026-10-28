"""Application configuration via pydantic-settings.

Settings are resolved from environment variables (and optionally a .env file).
No real credentials, APAAR identifiers or student data should appear here.
"""
from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ------------------------------------------------------------------
    # Database
    # ------------------------------------------------------------------
    DATABASE_URL: str = Field(
        default="sqlite+aiosqlite:///./apaar_dev.db",
        description="Async SQLAlchemy database URL. Defaults to local SQLite for development.",
    )
    DATABASE_MIGRATION_URL: str = Field(
        default="sqlite:///./apaar_dev.db",
        description=(
            "Synchronous SQLAlchemy URL for Alembic migrations. "
            "For PostgreSQL: postgresql+psycopg://apaar:apaar@localhost:5432/apaar_dev."
        ),
    )

    # ------------------------------------------------------------------
    # Security
    # ------------------------------------------------------------------
    SECRET_KEY: str = Field(
        default="change-me-in-production",
        description="HMAC/JWT signing key. Must be overridden in production.",
    )
    HMAC_KEY: str = Field(
        default="change-me-apaar-hmac-key",
        description="Key used to derive the APAAR HMAC lookup token. "
        "Keep out of version control.",
    )
    ALGORITHM: str = Field(
        default="HS256",
        description="JWT signing algorithm. HS256 is used for the dev mock JWT only.",
    )

    # ------------------------------------------------------------------
    # OIDC
    # ------------------------------------------------------------------
    OIDC_ISSUER: str = Field(
        default="http://localhost:8080/realms/apaar",
        description="OIDC issuer URL (e.g. Keycloak realm).",
    )
    OIDC_AUDIENCE: str = Field(
        default="apaar-core",
        description="Expected 'aud' claim in access tokens.",
    )

    # ------------------------------------------------------------------
    # Application behaviour
    # ------------------------------------------------------------------
    DEBUG: bool = Field(default=False, description="Enable debug mode and API docs.")
    LOG_LEVEL: str = Field(
        default="INFO",
        description="Python logging level: DEBUG, INFO, WARNING, ERROR, CRITICAL.",
    )

    # Prototype safety switch — must always be True for this prototype.
    SYNTHETIC_MODE: bool = Field(
        default=True,
        description=(
            "When True the system operates exclusively with synthetic/mock data. "
            "This must never be set to False in the prototype."
        ),
    )

    # ------------------------------------------------------------------
    # Upload / row limits
    # ------------------------------------------------------------------
    MAX_UPLOAD_BYTES: int = Field(
        default=10_485_760,  # 10 MiB
        description="Maximum allowed upload size in bytes.",
    )
    MAX_ROWS: int = Field(
        default=10_000,
        description="Maximum rows accepted per submission batch.",
    )
    MAX_COLUMNS: int = Field(
        default=50,
        description="Maximum columns accepted per submission CSV.",
    )

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------
    REPORT_FRESHNESS_TARGET_SECONDS: int = Field(
        default=60,
        description="Target maximum staleness (seconds) for pre-computed reports.",
    )

    # ------------------------------------------------------------------
    # CORS
    # ------------------------------------------------------------------
    ALLOWED_ORIGINS: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:5173"],
        description="List of allowed CORS origins.",
    )

    # ------------------------------------------------------------------
    # Synthetic / mock provider
    # ------------------------------------------------------------------
    MOCK_PROVIDER_DELAY_MS: int = Field(
        default=0,
        description="Artificial delay for the mock APAAR provider (ms).",
    )
    FIXTURE_VERSION: str = Field(
        default="v1",
        description="Version tag stamped on all synthetic fixture records.",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
