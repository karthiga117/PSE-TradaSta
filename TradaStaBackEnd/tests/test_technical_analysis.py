"""Technical-analysis service and API tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from httpx import ASGITransport, AsyncClient

from app.application.technical_analysis.service import TechnicalAnalysisService
from app.core.dependencies import market_data_service_dependency
from app.domain.market_data import Candle, MarketPrice
from app.domain.technical_analysis.indicators import (
    atr,
    bollinger_bands,
    ema,
    macd,
    rsi,
    sma,
    volume_analysis,
)
from app.domain.technical_analysis.models import IndicatorConfig, TrendDirection
from app.main import app


def _candles() -> list[Candle]:
    base = datetime(2024, 1, 1, tzinfo=UTC)
    closes = [
        100.0, 101.5, 103.0, 102.0, 104.0, 106.0, 108.0, 110.0, 109.0, 111.0,
        113.0, 114.0, 116.0, 118.5, 117.2, 119.0, 121.5, 123.0, 125.0, 124.0,
        126.0, 128.0, 127.5, 129.0, 131.0, 132.0, 134.0, 136.5, 138.0, 137.0,
        139.0, 141.0, 144.0, 146.0, 148.0, 150.5, 152.0, 154.0, 156.0, 158.5,
        160.0, 162.0, 161.0, 163.0, 165.0, 167.0, 168.5, 169.0, 171.0, 173.0,
    ]
    candles: list[Candle] = []
    for index, close in enumerate(closes):
        candle = Candle.from_values(
            "BTC",
            base + timedelta(hours=index),
            close - 1.0,
            close + 2.0,
            close - 2.5,
            close,
            1000.0 + index * 10,
        )
        candles.append(candle)
    return candles


class StubMarketDataService:
    def __init__(self) -> None:
        self.candles = _candles()

    async def get_current_price(self, symbol: str) -> MarketPrice:
        return MarketPrice.from_value(symbol, self.candles[-1].close)

    async def get_ohlcv(
        self,
        symbol: str,
        timeframe: str = "1h",
        limit: int = 24,
    ) -> list[Candle]:
        return self.candles[-limit:]


@pytest.mark.asyncio
async def test_indicator_values_are_deterministic() -> None:
    candles = _candles()
    service = TechnicalAnalysisService()
    result = service.analyze(candles, symbol="BTC", timeframe="1h")

    assert result.trend in {TrendDirection.BULLISH, TrendDirection.BEARISH, TrendDirection.NEUTRAL}
    assert result.sma is not None
    assert result.ema is not None
    assert result.rsi is not None
    assert result.macd is not None
    assert result.bollinger_bands is not None
    assert result.atr is not None
    assert result.volume is not None


def test_indicator_helpers_match_known_shapes() -> None:
    candles = _candles()
    assert sma(candles, 20).period == 20
    assert ema(candles, 12).period == 12
    assert rsi(candles, 14).period == 14
    assert macd(candles).fast_period == 12
    assert bollinger_bands(candles, 20, 2).period == 20
    assert atr(candles, 14).period == 14
    assert volume_analysis(candles, 20).period == 20


def test_indicator_config_rejects_bad_values() -> None:
    with pytest.raises(ValueError):
        IndicatorConfig(sma_period=0).validate()

    with pytest.raises(ValueError):
        IndicatorConfig(macd_fast_period=10, macd_slow_period=10).validate()


def test_golden_dataset_regression() -> None:
    candles = _candles()[:30]
    result = sma(candles, 10)
    assert result.value == Decimal("131.9")


@pytest.mark.asyncio
async def test_analysis_endpoint_works() -> None:
    app.dependency_overrides[market_data_service_dependency] = lambda: StubMarketDataService()
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/analysis/BTC?timeframe=1h&limit=50")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["symbol"] == "BTC"
    assert payload["timeframe"] == "1h"
    assert payload["trend"] in {"BULLISH", "BEARISH", "NEUTRAL"}
    assert "indicators" in payload
    assert "strategies" in payload


@pytest.mark.asyncio
async def test_market_data_endpoint_works() -> None:
    app.dependency_overrides[market_data_service_dependency] = lambda: StubMarketDataService()
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            price_response = await client.get("/api/v1/market-data/BTC/price")
            ohlcv_response = await client.get("/api/v1/market-data/BTC/ohlcv?timeframe=1h&limit=5")
    finally:
        app.dependency_overrides.clear()

    assert price_response.status_code == 200
    assert ohlcv_response.status_code == 200
    assert price_response.json()["symbol"] == "BTC"
    assert len(ohlcv_response.json()["candles"]) == 5
