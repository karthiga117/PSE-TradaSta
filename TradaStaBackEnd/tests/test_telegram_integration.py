"""Telegram integration tests."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.application.trading_analysis_service import normalize_symbol, parse_telegram_command
from app.application.knowledge.retrieval_service import SemanticRetrievalService
from app.application.market_data_service import MarketDataService
from app.domain.market_data import Candle, MarketPrice


class StubMarketDataService:
    async def get_current_price(self, symbol: str) -> MarketPrice:
        return MarketPrice.from_value(symbol, "65000.00", timestamp=datetime(2024, 1, 1, tzinfo=UTC))

    async def get_ohlcv(self, symbol: str, timeframe: str = "1h", limit: int = 24) -> list[Candle]:
        return [
            Candle.from_values(
                symbol,
                datetime(2024, 1, 1, 0, 0, tzinfo=UTC),
                60000,
                62000,
                59000,
                61000,
                1000,
            ),
            Candle.from_values(
                symbol,
                datetime(2024, 1, 1, 0, 5, tzinfo=UTC),
                61000,
                63000,
                60000,
                62500,
                1000,
            ),
            Candle.from_values(
                symbol,
                datetime(2024, 1, 1, 0, 10, tzinfo=UTC),
                62500,
                64000,
                62000,
                63500,
                1000,
            ),
        ]


@pytest.mark.asyncio
async def test_trading_analysis_service_normalizes_and_orchestrates() -> None:
    service = MarketDataService(StubMarketDataService())
    orchestration = __import__("app.application.trading_analysis_service", fromlist=["TradingAnalysisService"]).TradingAnalysisService(
        market_data_service=service,
        retrieval_service=SemanticRetrievalService(),
    )

    result = await orchestration.analyze("btc")

    assert result["symbol"] == "BTCUSDT"
    assert result["signal"] in {"BUY", "SELL", "HOLD"}
    assert result["risk_decision"].approved in {True, False}


def test_symbol_normalization_supports_common_aliases() -> None:
    assert normalize_symbol("btc") == "BTCUSDT"
    assert normalize_symbol("BTCUSDT") == "BTCUSDT"
    assert normalize_symbol("eth") == "ETHUSDT"


def test_telegram_command_parser_detects_supported_intents() -> None:
    assert parse_telegram_command("/price BTCUSDT")["intent"] == "price"
    assert parse_telegram_command("Analyze ETHUSDT")["intent"] == "analyze"
    assert parse_telegram_command("What is the risk for BTCUSDT?")["intent"] == "risk"
    assert parse_telegram_command("/help")["intent"] == "help"
