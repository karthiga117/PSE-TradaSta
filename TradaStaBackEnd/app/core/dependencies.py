"""Dependency injection primitives for application services."""

from collections.abc import Iterator

from app.application.market_data_service import MarketDataService
from app.application.risk_management.service import RiskManagementService
from app.application.signal_engine import SignalEngine
from app.application.technical_analysis.service import TechnicalAnalysisService
from app.application.technical_analysis.strategies import build_default_registry
from app.core.config import Settings, get_settings
from app.domain.risk_management.models import RiskConfiguration
from app.infrastructure.market_data.providers.coingecko import CoinGeckoMarketDataProvider


def settings_dependency() -> Iterator[Settings]:
    """Provide configuration through FastAPI's dependency system."""
    yield get_settings()


def market_data_service_dependency() -> MarketDataService:
    """Provide the configured market-data service for API handlers."""
    return MarketDataService(CoinGeckoMarketDataProvider())


def technical_analysis_service_dependency() -> TechnicalAnalysisService:
    """Provide the deterministic technical-analysis service."""
    return TechnicalAnalysisService()


def risk_management_service_dependency() -> RiskManagementService:
    """Provide the configured risk-management engine."""
    settings = get_settings()
    risk_config = RiskConfiguration(
        risk_per_trade_percent=settings.risk_per_trade_percent,
        max_risk_per_trade=settings.max_risk_per_trade,
        max_position_size=settings.max_position_size,
        max_portfolio_exposure=settings.max_portfolio_exposure,
        max_daily_loss=settings.max_daily_loss,
        max_drawdown_percent=settings.max_drawdown_percent,
        min_risk_reward_ratio=settings.min_risk_reward_ratio,
        max_open_positions=settings.max_open_positions,
        stop_loss_required=settings.stop_loss_required,
        take_profit_required=settings.take_profit_required,
    )
    return RiskManagementService(config=risk_config)


def signal_engine_dependency() -> SignalEngine:
    """Provide the trading signal engine with all required collaborators."""
    settings = get_settings()
    market_data_service = MarketDataService(CoinGeckoMarketDataProvider())
    technical_service = TechnicalAnalysisService()
    risk_service = risk_management_service_dependency()
    return SignalEngine(
        market_data_service=market_data_service,
        technical_analysis_service=technical_service,
        strategy_registry=build_default_registry(),
        risk_service=risk_service,
        settings=settings,
    )
