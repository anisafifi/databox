import os
from dataclasses import dataclass, field


def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


@dataclass(frozen=True)
class Settings:
    app_name: str = "databox"
    environment: str = os.getenv("DATABOX_ENV", "dev")
    cors_allow_origins: list[str] = field(
        default_factory=lambda: _split_csv(os.getenv("DATABOX_CORS_ORIGINS", "*"))
    )
    local_data_path: str = os.getenv("DATABOX_LOCAL_DATA_PATH", "data/sample.json")
    api_keys_path: str = os.getenv("DATABOX_API_KEYS_PATH", "data/api_keys.json")
    api_key_retention_days: int = int(os.getenv("DATABOX_API_KEY_RETENTION_DAYS", "90"))
    rate_limit_per_minute: int = int(os.getenv("DATABOX_RATE_LIMIT_PER_MINUTE", "60"))
    log_level: str = os.getenv("DATABOX_LOG_LEVEL", "INFO")
    ntp_servers: list[str] = field(
        default_factory=lambda: _split_csv(
            os.getenv(
                "DATABOX_NTP_SERVERS",
                "time.hixbe.com,time.google.com,time.cloudflare.com",
            )
        )
    )
    ntp_timeout_seconds: int = int(os.getenv("DATABOX_NTP_TIMEOUT_SECONDS", "2"))
    http_source_url: str | None = os.getenv("DATABOX_HTTP_SOURCE_URL") or None


settings = Settings()
