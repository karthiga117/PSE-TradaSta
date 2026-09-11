"""Market-data service tests."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.application.interfaces import IMarketDataProvider
from app.application.market_data_service import MarketDataService
from app.domain.market_data import Candle, MarketPrice
from app.infrastructure.market_data.providers.coingecko import CoinGeckoMarketDataProvider


class StubProvider(IMarketDataProvider):
    async def get_current_price(
        self,
        symbol: str,
        *,
        cancellation_token: object | None = None,
    ) -> MarketPrice:
        return MarketPrice.from_value(
            symbol,
            "123.45",
            timestamp=datetime(2024, 1, 1, tzinfo=UTC),
        )

    async def get_ohlcv(
        self,
        symbol: str,
        timeframe: str = "1h",
        limit: int = 24,
        *,
        cancellation_token: object | None = None,
    ) -> list[Candle]:
        return [
            Candle.from_values(
                symbol,
                datetime(2024, 1, 1, tzinfo=UTC),
                122.0,
                123.0,
                121.0,
                123.45,
                100.0,
            )
        ]

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
        return await self.get_ohlcv(symbol, timeframe=timeframe, limit=limit or 1)


@pytest.mark.asyncio
async def test_market_data_service_uses_provider_abstraction() -> None:
    service = MarketDataService(StubProvider())

    price = await service.get_current_price("btc")
    snapshot = await service.get_market_snapshot("btc")

    assert price.price == Decimal("123.45")
    assert price.symbol == "BTC"
    assert snapshot.price == Decimal("123.45")
    assert snapshot.volume_24h == Decimal("100.0")


def test_coin_gecko_provider_normalizes_symbols() -> None:
    provider = CoinGeckoMarketDataProvider()

    assert provider._normalise_symbol("btc-usd") == "bitcoin"
    assert provider._normalise_symbol("eth") == "ethereum"
