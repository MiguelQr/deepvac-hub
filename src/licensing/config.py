"""Environment-based configuration, shared by both apps/api and apps/web.

Fails fast at startup when a critical secret is missing outside local
development, per the requirement that misconfiguration must not silently
degrade security.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = Field(default="development", alias="APP_ENV")

    database_url: str = Field(alias="DATABASE_URL")
    test_database_url: str | None = Field(default=None, alias="TEST_DATABASE_URL")

    flask_secret_key: str = Field(alias="FLASK_SECRET_KEY")

    license_signing_key_id: str = Field(alias="LICENSE_SIGNING_KEY_ID")
    license_signing_private_key_path: str | None = Field(
        default=None, alias="LICENSE_SIGNING_PRIVATE_KEY_PATH"
    )
    license_signing_public_key: str | None = Field(
        default=None, alias="LICENSE_SIGNING_PUBLIC_KEY"
    )

    public_base_url: str = Field(alias="PUBLIC_BASE_URL")
    api_base_url: str = Field(alias="API_BASE_URL")
    management_base_url: str = Field(alias="MANAGEMENT_BASE_URL")

    session_cookie_secure: bool = Field(default=True, alias="SESSION_COOKIE_SECURE")
    session_idle_timeout_minutes: int = Field(default=60, alias="SESSION_IDLE_TIMEOUT_MINUTES")
    trusted_proxy_count: int = Field(default=1, alias="TRUSTED_PROXY_COUNT")

    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    activation_ttl_seconds: int = Field(default=600, alias="ACTIVATION_TTL_SECONDS")
    refresh_challenge_ttl_seconds: int = Field(
        default=120, alias="REFRESH_CHALLENGE_TTL_SECONDS"
    )
    default_license_validity_days: int = Field(
        default=365, alias="DEFAULT_LICENSE_VALIDITY_DAYS"
    )

    @field_validator("app_env")
    @classmethod
    def _normalize_env(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"development", "test", "staging", "production"}:
            raise ValueError(f"Unknown APP_ENV: {value!r}")
        return normalized

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    def require_signing_key_path(self) -> str:
        """Raise clearly if the signing-api process was started without a
        private key configured. Called by apps/api at startup, not at import
        time, so read-only management/dev tooling doesn't need the secret.
        """
        if not self.license_signing_private_key_path:
            raise RuntimeError(
                "LICENSE_SIGNING_PRIVATE_KEY_PATH is not set. "
                "The licensing API cannot issue or renew certificates without it."
            )
        return self.license_signing_private_key_path

    def validate_for_production(self) -> None:
        if not self.is_production:
            return
        missing = []
        if self.flask_secret_key.startswith("change-me"):
            missing.append("FLASK_SECRET_KEY")
        if not self.license_signing_private_key_path:
            missing.append("LICENSE_SIGNING_PRIVATE_KEY_PATH")
        if not self.session_cookie_secure:
            missing.append("SESSION_COOKIE_SECURE must be true in production")
        if missing:
            raise RuntimeError(
                "Refusing to start in production with invalid configuration: "
                + ", ".join(missing)
            )


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
