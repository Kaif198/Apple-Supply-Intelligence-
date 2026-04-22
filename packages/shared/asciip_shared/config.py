"""Configuration loaded from environment variables with fail-fast validation.

Satisfies Requirement 22 (Configuration and Extensibility). Every service in
the monorepo imports `get_settings()` for a memoized, validated `Settings`
instance. Invalid values cause immediate startup failure with descriptive
errors via `ConfigurationError`.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic import ValidationError as PydanticValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

from asciip_shared.exceptions import ConfigurationError

_ENV_FILE = Path(os.environ.get("ASCIIP_ENV_FILE", ".env"))

Environment = Literal["development", "staging", "production", "test"]
LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


class Settings(BaseSettings):
    """Single source of truth for runtime configuration.

    Values come from (in order of precedence):

    1. Actual environment variables
    2. Values set in ``.env`` (path overridable via ``ASCIIP_ENV_FILE``)
    3. The defaults declared below
    """

    model_config = SettingsConfigDict(
        env_file=_ENV_FILE if _ENV_FILE.exists() else None,
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
        populate_by_name=True,
    )

    # -- Runtime ------------------------------------------------------------
    env: Environment = Field(default="development", alias="ASCIIP_ENV")
    log_level: LogLevel = Field(default="INFO", alias="ASCIIP_LOG_LEVEL")
    log_pretty: bool = Field(default=True, alias="ASCIIP_LOG_PRETTY")
    service_name: str = Field(default="asciip-api", alias="ASCIIP_SERVICE_NAME")
    version: str = Field(default="0.1.0", alias="ASCIIP_VERSION")
    build_sha: str = Field(default="", alias="ASCIIP_BUILD_SHA")
    cors_origins: str = Field(
        default="http://localhost:3000,http://127.0.0.1:3000",
        alias="ASCIIP_CORS_ORIGINS",
    )

    # -- Data paths ---------------------------------------------------------
    data_dir: Path = Field(default=Path("./data"), alias="ASCIIP_DATA_DIR")
    duckdb_path: Path = Field(
        default=Path("./data/features/asciip.duckdb"),
        alias="ASCIIP_DUCKDB_PATH",
    )
    snapshots_dir: Path = Field(default=Path("./data/snapshots"), alias="ASCIIP_SNAPSHOTS_DIR")
    models_dir: Path = Field(default=Path("./data/models"), alias="ASCIIP_MODELS_DIR")
    exports_dir: Path = Field(default=Path("./data/exports"), alias="ASCIIP_EXPORTS_DIR")
    raw_dir: Path = Field(default=Path("./data/raw"), alias="ASCIIP_RAW_DIR")

    # -- External API keys (all optional) -----------------------------------
    fred_api_key: SecretStr | None = Field(default=None, alias="FRED_API_KEY")
    marketaux_api_key: SecretStr | None = Field(default=None, alias="MARKETAUX_API_KEY")
    finnhub_api_key: SecretStr | None = Field(default=None, alias="FINNHUB_API_KEY")
    comtrade_api_key: SecretStr | None = Field(default=None, alias="COMTRADE_API_KEY")
    nominatim_user_agent: str = Field(
        default="asciip/0.1 (ops@example.com)",
        alias="ASCIIP_NOMINATIM_USER_AGENT",
    )
    apple_supplier_pdf_url: str = Field(default="", alias="APPLE_SUPPLIER_PDF_URL")

    # -- Alerts -------------------------------------------------------------
    smtp_host: str = Field(default="", alias="ASCIIP_SMTP_HOST")
    smtp_port: int = Field(default=587, alias="ASCIIP_SMTP_PORT", ge=1, le=65_535)
    smtp_username: SecretStr | None = Field(default=None, alias="ASCIIP_SMTP_USERNAME")
    smtp_password: SecretStr | None = Field(default=None, alias="ASCIIP_SMTP_PASSWORD")
    smtp_from: str = Field(default="asciip@example.com", alias="ASCIIP_SMTP_FROM")
    smtp_to: str = Field(default="", alias="ASCIIP_SMTP_TO")
    alert_webhook_url: str = Field(default="", alias="ASCIIP_ALERT_WEBHOOK_URL")

    # -- DCF / Monte Carlo --------------------------------------------------
    dcf_wacc: float = Field(default=0.086, alias="ASCIIP_DCF_WACC", gt=0, lt=1)
    dcf_terminal_growth: float = Field(
        default=0.025, alias="ASCIIP_DCF_TERMINAL_GROWTH", ge=0, lt=0.1
    )
    dcf_tax_rate: float = Field(default=0.16, alias="ASCIIP_DCF_TAX_RATE", ge=0, lt=1)
    dcf_horizon_years: int = Field(default=5, alias="ASCIIP_DCF_HORIZON_YEARS", ge=1, le=15)
    mc_iterations: int = Field(default=10_000, alias="ASCIIP_MC_ITERATIONS", ge=100, le=1_000_000)
    mc_seed: int = Field(default=20260101, alias="ASCIIP_MC_SEED")

    # -- ML hyperparameters -------------------------------------------------
    xgb_params: str = Field(default="", alias="ASCIIP_XGB_PARAMS")
    prophet_seasonality_strength: float = Field(
        default=10.0, alias="ASCIIP_PROPHET_SEASONALITY_STRENGTH", gt=0
    )
    ridge_alpha_max: float = Field(default=100.0, alias="ASCIIP_RIDGE_ALPHA_MAX", gt=0)

    # -- Refresh intervals --------------------------------------------------
    refresh_commodity_seconds: int = Field(
        default=3_600, alias="ASCIIP_REFRESH_COMMODITY_SECONDS", ge=60
    )
    refresh_trade_seconds: int = Field(default=21_600, alias="ASCIIP_REFRESH_TRADE_SECONDS", ge=60)
    refresh_supplier_seconds: int = Field(
        default=7_776_000, alias="ASCIIP_REFRESH_SUPPLIER_SECONDS", ge=3_600
    )

    # -- Rate limiting ------------------------------------------------------
    rate_limit_default: str = Field(default="100/minute", alias="ASCIIP_RATE_LIMIT_DEFAULT")
    rate_limit_scenarios: str = Field(default="30/minute", alias="ASCIIP_RATE_LIMIT_SCENARIOS")
    rate_limit_exports: str = Field(default="10/minute", alias="ASCIIP_RATE_LIMIT_EXPORTS")
    rate_limit_stream: str = Field(default="10/minute", alias="ASCIIP_RATE_LIMIT_STREAM")

    # Numeric equivalent of rate_limit_default used by the in-process limiter.
    rate_limit_capacity: int = Field(
        default=100, alias="ASCIIP_RATE_LIMIT_CAPACITY", ge=1, le=10_000
    )

    # -- Scheduler ---------------------------------------------------------
    enable_scheduler: bool = Field(default=False, alias="ASCIIP_ENABLE_SCHEDULER")

    # ----------------------------------------------------------------------
    # Derived helpers
    # ----------------------------------------------------------------------

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.env == "production"

    def source_enabled(self, source: str) -> bool:
        """Return True when the given external source has credentials configured."""
        key = {
            "fred": self.fred_api_key,
            "marketaux": self.marketaux_api_key,
            "finnhub": self.finnhub_api_key,
            "comtrade": self.comtrade_api_key,
        }.get(source.lower())
        return bool(key and key.get_secret_value())

    def resolve(self, path: Path) -> Path:
        """Return ``path`` resolved against ``data_dir`` when relative."""
        return path if path.is_absolute() else (self.data_dir.parent / path).resolve()

    @field_validator("data_dir", "snapshots_dir", "models_dir", "exports_dir", "raw_dir")
    @classmethod
    def _non_empty_path(cls, v: Path) -> Path:
        if str(v).strip() == "":
            raise ValueError("path must not be empty")
        return v

    @field_validator("cors_origins")
    @classmethod
    def _cors_no_wildcard_in_prod(cls, v: str, info):  # type: ignore[no-untyped-def]
        env_value = (info.data or {}).get("env")
        if env_value == "production" and "*" in v:
            raise ValueError("wildcard CORS origins are not permitted in production")
        return v


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide settings singleton.

    Raises ``ConfigurationError`` (with field-level detail) when any value
    fails validation. This is the single throw point the operator sees at
    startup if their environment is misconfigured.
    """
    try:
        return Settings()  # type: ignore[call-arg]
    except PydanticValidationError as exc:
        raise ConfigurationError(
            "invalid ASCIIP configuration",
            detail={"errors": exc.errors()},
        ) from exc


def reset_settings_cache() -> None:
    """Test helper: invalidate the memoized settings."""
    get_settings.cache_clear()
