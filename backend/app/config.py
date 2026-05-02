import os
from dataclasses import dataclass
from functools import lru_cache


@dataclass(frozen=True)
class Settings:
    """Runtime configuration for the Slack lunch bot backend."""

    slack_signing_secret: str | None = None
    default_locale: str = "ko-KR"
    default_timezone: str = "Asia/Seoul"
    restaurant_search_radius_meters: int = 150
    conversation_ttl_minutes: int = 30
    slack_response_timeout_seconds: float = 5.0
    upstream_timeout_seconds: float = 3.0
    environment: str = "development"

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            slack_signing_secret=os.getenv("SLACK_SIGNING_SECRET"),
            default_locale=os.getenv("DEFAULT_LOCALE", "ko-KR"),
            default_timezone=os.getenv("DEFAULT_TIMEZONE", "Asia/Seoul"),
            restaurant_search_radius_meters=int(
                os.getenv("RESTAURANT_SEARCH_RADIUS_METERS", "150")
            ),
            conversation_ttl_minutes=int(os.getenv("CONVERSATION_TTL_MINUTES", "30")),
            slack_response_timeout_seconds=float(
                os.getenv("SLACK_RESPONSE_TIMEOUT_SECONDS", "5")
            ),
            upstream_timeout_seconds=float(os.getenv("UPSTREAM_TIMEOUT_SECONDS", "3")),
            environment=os.getenv("ENVIRONMENT", "development"),
        )


@lru_cache
def get_settings() -> Settings:
    return Settings.from_env()
