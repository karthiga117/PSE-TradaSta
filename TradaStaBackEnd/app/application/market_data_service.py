"""Use-case service for cryptocurrency market data."""

from __future__ import annotations

from datetime import datetime

from app.application.interfaces import IMarketDataProvider
from app.core.exceptions import MarketDataError
from app.domain.market_data import Candle, MarketPrice, MarketSnapshot


class MarketDataService:
    """Application-layer orchestrator used by API handlers and other services."""

    def __init__(self, provider: IMarketDataProvider) -> None:
        self._provider = provider

    async def get_current_price(self, symbol: str) -> MarketPrice:
        """Return the most recent spot price."""
        try:
            return await self._provider.get_current_price(symbol)
        except Exception as exc:  # pragma: no cover - defensive application boundary
            raise MarketDataError(f"Unable to fetch current price for {symbol}: {exc}") from exc

    async def get_ohlcv(
        self,
        symbol: str,
        timeframe: str = "1h",
        limit: int = 24,
    ) -> list[Candle]:
        """Return OHLCV candles for the requested symbol and timeframe."""
        try:
            return await self._provider.get_ohlcv(symbol, timeframe=timeframe, limit=limit)
        except Exception as exc:  # pragma: no cover - defensive application boundary
            raise MarketDataError(
                f"Unable to fetch OHLCV data for {symbol} at {timeframe}: {exc}"
            ) from exc

    async def get_historical_data(
        self,
        symbol: str,
        timeframe: str = "1h",
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int | None = None,
    ) -> list[Candle]:
        """Return historical pricing data for a requested time window."""
        try:
            return await self._provider.get_historical_data(
                symbol,
                timeframe=timeframe,
                start=start,
                end=end,
                limit=limit,
            )
        except Exception as exc:  # pragma: no cover - defensive application boundary
            raise MarketDataError(
                f"Unable to fetch historical data for {symbol} at {timeframe}: {exc}"
            ) from exc

    async def get_market_snapshot(
        self,
        symbol: str,
        timeframe: str = "1h",
        limit: int = 24,
    ) -> MarketSnapshot:
        """Compose a market snapshot from the latest price and recent candles."""
        price = await self.get_current_price(symbol)
        candles = await self.get_ohlcv(symbol, timeframe=timeframe, limit=limit)
        last_candle = candles[-1] if candles else None

        return MarketSnapshot(
            symbol=price.symbol,
            price=price.price,
            timestamp=price.timestamp,
            volume_24h=last_candle.volume if last_candle is not None else None,
        )


__all__ = ["MarketDataService"]
