from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "Kairos"
    environment: Literal["development", "staging", "production", "test"] = "development"
    log_level: str = "INFO"

    database_url: str = "postgresql+asyncpg://kairos:kairos@kairos-postgres:5432/kairos"
    redis_url: str = "redis://kairos-redis:6379/0"

    jwt_secret: str = "change-me-in-production-kairos-jwt-secret"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 14

    api_key_pepper: str = "change-me-in-production-kairos-api-key-pepper"
    cors_origins: str = "http://localhost:5173,http://localhost:8080,http://localhost"
    frontend_url: str = "http://localhost:5173"

    demo_mode: bool = True
    seed_demo: bool = True
    demo_user_email: str = "demo@kairos.app"
    demo_user_password: str = "KairosDemo!2026"
    public_api_url: str = "http://kairos-api:8000"
    public_mcp_url: str = "http://localhost:8001/mcp"
    mcp_allowed_hosts: str = (
        "localhost,localhost:*,127.0.0.1,127.0.0.1:*,kairos-mcp,kairos-mcp:*,"
        "host.docker.internal,host.docker.internal:*"
    )
    mcp_allowed_origins: str = ""

    llm_provider: Literal["anthropic", "openai_compatible", "heuristic"] = "heuristic"
    llm_timeout_seconds: float = 45.0
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-20250514"
    openai_base_url: str = "http://host.docker.internal:11434/v1"
    openai_api_key: str = "not-needed"
    openai_model: str = "qwen2.5:14b"

    linkedin_connector_url: str = ""
    linkedin_connector_token: str = ""
    linkedin_webhook_secret: str = "change-me-linkedin-webhook-secret"

    unipile_base_url: str = ""
    unipile_dsn: str = ""
    unipile_api_key: str = ""
    unipile_timeout_seconds: float = 20.0
    unipile_max_retries: int = 5

    default_timezone: str = "Europe/Paris"
    send_window_start: int = 8
    send_window_end: int = 19
    demo_auto_replies: bool = True
    min_outbound_interval_seconds: int = 45
    scheduler_run_actions_interval_seconds: int = 60
    scheduler_run_enrollments_interval_seconds: int = 300
    scheduler_run_sync_accounts_interval_seconds: int = 900

    sentry_dsn: str = ""
    posthog_key: str = ""

    @field_validator("cors_origins")
    @classmethod
    def normalize_cors(cls, value: str) -> str:
        return value.strip()

    @property
    def cors_origin_list(self) -> list[str]:
        origins = [item.strip() for item in self.cors_origins.split(",") if item.strip()]
        if "*" in origins:
            return ["*"]
        return origins

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
