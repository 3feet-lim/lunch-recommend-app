from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for the Slack lunch bot backend."""

    slack_signing_secret: str = Field(default="", alias="SLACK_SIGNING_SECRET")
    default_locale: str = Field(default="ko-KR", alias="DEFAULT_LOCALE")
    default_timezone: str = Field(default="Asia/Seoul", alias="DEFAULT_TIMEZONE")
    restaurant_search_radius_meters: int = Field(
        default=150, alias="RESTAURANT_SEARCH_RADIUS_METERS"
    )
    conversation_ttl_minutes: int = Field(default=30, alias="CONVERSATION_TTL_MINUTES")
    slack_response_timeout_seconds: float = Field(
        default=5.0, alias="SLACK_RESPONSE_TIMEOUT_SECONDS"
    )
    upstream_timeout_seconds: float = Field(default=3.0, alias="UPSTREAM_TIMEOUT_SECONDS")
    environment: str = Field(default="development", alias="ENVIRONMENT")

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[2] / ".env",
        extra="ignore",
        populate_by_name=True,
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
