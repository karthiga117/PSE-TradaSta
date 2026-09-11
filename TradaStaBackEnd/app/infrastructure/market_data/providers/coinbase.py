"""Backward-compatible Coinbase provider alias."""

from app.infrastructure.market_data.providers.coingecko import (
    CoinbaseMarketDataProvider,
    CoinGeckoMarketDataProvider,
    CoinMarketDataProvider,
)

__all__ = [
    "CoinGeckoMarketDataProvider",
    "CoinMarketDataProvider",
    "CoinbaseMarketDataProvider",
]
