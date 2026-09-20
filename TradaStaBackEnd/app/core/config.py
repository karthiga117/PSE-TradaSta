"""Application configuration."""

from decimal import Decimal
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings loaded from environment variables and .env."""

    app_name: str = "TradaSta AI"
    app_version: str = "0.1.0"
    environment: str = "development"
    debug: bool = False
    log_level: str = "INFO"
    api_v1_prefix: str = "/api/v1"
    database_url: str = "sqlite:///./tradasta_auth.db"
    auth_required_for_trading: bool = False
    jwt_secret_key: str = "change-this-to-a-random-32-byte-secret-value"

    @property
    def require_auth_for_trading(self) -> bool:
        """Backward-compatible alias for the trading-auth switch."""
        return self.auth_required_for_trading
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7
    auth_login_rate_limit: int = 5
    auth_login_lockout_seconds: int = 300
    ai_request_rate_limit: int = 30
    cors_allowed_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:4200",
            "http://127.0.0.1:4200",
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ]
    )
    market_data_provider: str = "coingecko"
    market_data_base_url: str = "https://api.coingecko.com/api/v3"
    market_data_timeout_seconds: float = 10.0
    knowledge_chunk_size: int = 600
    knowledge_chunk_overlap: int = 80
    knowledge_max_top_k: int = 10
    knowledge_min_score: float = 0.0
    knowledge_dataset_directory: str = "app/data/knowledge"
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
    telegram_bot_token: str = ""
    telegram_webhook_secret: str = ""
    telegram_webhook_url: str | None = None
    telegram_allowed_chat_ids: list[int] = Field(default_factory=list)
    telegram_mode: str = "webhook"
    telegram_api_base_url: str = "https://api.telegram.org"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    def validate_required_security_settings(self) -> None:
        """Fail fast in production when required auth settings are missing or weak."""
        if self.jwt_secret_key and len(self.jwt_secret_key.encode("utf-8")) < 32:
            raise ValueError("JWT secret key must be at least 32 characters long.")
        if self.environment.lower() == "production" and not self.jwt_secret_key:
            raise ValueError("JWT secret key is required in production.")


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide settings instance."""
    return Settings()
