"""Market data abstractions used by the application layer."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol, runtime_checkable

from app.domain.market_data import Candle, MarketPrice


@runtime_checkable
class IMarketDataProvider(Protocol):
    """Provider contract for all market-data integrations."""

    async def get_current_price(
        self,
        symbol: str,
        *,
        cancellation_token: object | None = None,
    ) -> MarketPrice:
        """Return the latest market price for the given symbol."""

    async def get_ohlcv(
        self,
        symbol: str,
        timeframe: str = "1h",
        limit: int = 24,
        *,
        cancellation_token: object | None = None,
    ) -> list[Candle]:
        """Return a sequence of OHLCV candles for the symbol."""

    async def get_historical_data(
        self,
        symbol: str,
        timeframe: str = "1h",
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int | None = None,
        *,
        cancellation_token: object | None = None,
    ) -> list[Candle]:
        """Return historical candles between a start and end timestamp."""


__all__ = ["IMarketDataProvider"]
