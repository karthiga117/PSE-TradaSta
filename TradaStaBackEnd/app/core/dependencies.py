"""Dependency injection primitives for application services."""

from collections.abc import Iterator

from app.application.knowledge.retrieval_service import SemanticRetrievalService
from app.application.market_data_service import MarketDataService
from app.core.config import Settings, get_settings
from app.infrastructure.market_data.providers.coingecko import CoinGeckoMarketDataProvider


def settings_dependency() -> Iterator[Settings]:
    """Provide configuration through FastAPI's dependency system."""
    yield get_settings()


def market_data_service_dependency() -> MarketDataService:
    """Provide the configured market-data service for API handlers."""
    return MarketDataService(CoinGeckoMarketDataProvider())


def context_retrieval_service_dependency() -> SemanticRetrievalService:
    """Provide the retrieval service used by context-aware endpoints."""
    return SemanticRetrievalService()
