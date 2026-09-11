"""Application configuration."""

from decimal import Decimal
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings loaded from environment variables and .env."""

    app_name: str = "TradaSta AI"
    app_version: str = "0.1.0"
    environment: str = "development"
    debug: bool = False
    log_level: str = "INFO"
    api_v1_prefix: str = "/api/v1"
    market_data_provider: str = "coingecko"
    market_data_base_url: str = "https://api.coingecko.com/api/v3"
    market_data_timeout_seconds: float = 10.0
    risk_per_trade_percent: Decimal = Decimal("0.01")
    max_risk_per_trade: Decimal | None = None
    max_position_size: Decimal = Decimal("1000000")
    max_portfolio_exposure: Decimal = Decimal("50000")
    max_daily_loss: Decimal = Decimal("500")
    max_drawdown_percent: Decimal = Decimal("0.10")
    min_risk_reward_ratio: Decimal = Decimal("2.0")
    max_open_positions: int = 5
    stop_loss_required: bool = True
    take_profit_required: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide settings instance."""
    return Settings()
