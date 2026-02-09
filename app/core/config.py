import os
from dataclasses import dataclass, field

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass


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
    ipinfo_token: str | None = os.getenv("DATABOX_IPINFO_TOKEN") or None
    ipinfo_lookup_base_url: str = os.getenv("DATABOX_IPINFO_LOOKUP_BASE_URL", "https://ipinfo.io")
    ipinfo_visitor_url: str = os.getenv("DATABOX_IPINFO_VISITOR_URL", "https://api.ipinfo.io/lite/me")
    ipinfo_timeout_seconds: int = int(os.getenv("DATABOX_IPINFO_TIMEOUT_SECONDS", "5"))
    math_eval_timeout_seconds: int = int(os.getenv("DATABOX_MATH_EVAL_TIMEOUT_SECONDS", "10"))
    math_max_expr_length: int = int(os.getenv("DATABOX_MATH_MAX_EXPR_LENGTH", "4096"))
    site_check_timeout_connect_seconds: int = int(
        os.getenv("DATABOX_SITE_CHECK_TIMEOUT_CONNECT_SECONDS", "3")
    )
    site_check_timeout_read_seconds: int = int(
        os.getenv("DATABOX_SITE_CHECK_TIMEOUT_READ_SECONDS", "5")
    )
    site_check_max_redirects: int = int(os.getenv("DATABOX_SITE_CHECK_MAX_REDIRECTS", "5"))
    site_check_user_agent: str = os.getenv(
        "DATABOX_SITE_CHECK_USER_AGENT",
        "databox/1.0 (+https://github.com/anisafifi/databox)",
    )
    site_check_allowlist: list[str] = field(
        default_factory=lambda: _split_csv(os.getenv("DATABOX_SITE_CHECK_ALLOWLIST", ""))
    )
    site_check_header_allowlist: list[str] = field(
        default_factory=lambda: _split_csv(
            os.getenv(
                "DATABOX_SITE_CHECK_HEADER_ALLOWLIST",
                "content-type,content-length,server,cache-control,location,date",
            )
        )
    )
    password_max_length: int = int(os.getenv("DATABOX_PASSWORD_MAX_LENGTH", "128"))
    dictionary_base_url: str = os.getenv(
        "DATABOX_DICTIONARY_BASE_URL",
        "https://api.dictionaryapi.dev/api/v2/entries",
    )
    dictionary_timeout_seconds: int = int(os.getenv("DATABOX_DICTIONARY_TIMEOUT_SECONDS", "5"))
    server_url: str | None = os.getenv("DATABOX_SERVER_URL") or None
    http_source_url: str | None = os.getenv("DATABOX_HTTP_SOURCE_URL") or None


settings = Settings()
