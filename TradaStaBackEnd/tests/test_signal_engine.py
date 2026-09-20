"""Tests for the deterministic trading signal engine."""

from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from app.application.risk_management.service import RiskManagementService
from app.application.signal_engine import SignalEngine
from app.application.technical_analysis.strategies import StrategyRegistry, TechnicalStrategy
from app.domain.market_data import Candle, MarketPrice
from app.domain.risk_management.models import RiskConfiguration
from app.domain.signal import SignalRequest, SignalValue
from app.domain.technical_analysis.models import (
    ATRResult,
    EMAResult,
    MACDResult,
    RSIResult,
    SMAResult,
    StrategyObservation,
    TechnicalAnalysisResult,
    TrendDirection,
)


def _make_candle(symbol: str, price: Decimal, offset: int) -> Candle:
    base = datetime(2024, 1, 1, tzinfo=None) + timedelta(minutes=offset)
    return Candle(
        symbol=symbol,
        timestamp=base,
        open=price,
        high=price + Decimal("1"),
        low=price - Decimal("1"),
        close=price,
        volume=Decimal("1000"),
    )


class FixedMarketDataService:
    def __init__(self, *, price: Decimal, candles: list[Candle]) -> None:
        self._price = MarketPrice(symbol="BTCUSDT", price=price)
        self._candles = candles

    async def get_current_price(self, symbol: str) -> MarketPrice:
        return self._price

    async def get_ohlcv(self, symbol: str, timeframe: str = "1h", limit: int = 24) -> list[Candle]:
        return self._candles


class FixedTechnicalAnalysisService:
    def __init__(self, analysis: TechnicalAnalysisResult) -> None:
        self._analysis = analysis

    def analyze(
        self,
        candles: list[Candle],
        *,
        symbol: str,
        timeframe: str = "1h",
    ) -> TechnicalAnalysisResult:
        return self._analysis


class PositiveTrendStrategy(TechnicalStrategy):
    name = "positive_trend"

    def evaluate(self, result: TechnicalAnalysisResult) -> StrategyObservation:
        return StrategyObservation(
            strategy_name=self.name,
            direction=result.trend,
            rationale="Trend is clearly bullish.",
            indicator_values={"trend": result.trend.value},
        )


@pytest.mark.asyncio
async def test_signal_engine_generates_buy_signal_when_risk_passes() -> None:
    candles = [_make_candle("BTCUSDT", Decimal("99"), i) for i in range(1, 120)]
    analysis = TechnicalAnalysisResult(
        symbol="BTCUSDT",
        timeframe="1h",
        timestamp=candles[-1].timestamp,
        trend=TrendDirection.BULLISH,
        sma=SMAResult(period=20, value=Decimal("95")),
        ema=EMAResult(period=12, value=Decimal("97")),
        rsi=RSIResult(period=14, value=Decimal("60")),
        macd=MACDResult(
            fast_period=12,
            slow_period=26,
            signal_period=9,
            macd=Decimal("2.5"),
            signal=Decimal("1.0"),
            histogram=Decimal("1.5"),
        ),
        atr=ATRResult(period=14, value=Decimal("5")),
        strategies=[
            StrategyObservation(
                strategy_name="positive_trend",
                direction=TrendDirection.BULLISH,
                rationale="Trend is bullish.",
                indicator_values={"trend": "BULLISH"},
            )
        ],
    )

    engine = SignalEngine(
        market_data_service=FixedMarketDataService(price=Decimal("100"), candles=candles),
        technical_analysis_service=FixedTechnicalAnalysisService(analysis),
        strategy_registry=StrategyRegistry([PositiveTrendStrategy()]),
        risk_service=RiskManagementService(
            config=RiskConfiguration(
                max_portfolio_exposure=Decimal("100000"),
                max_daily_loss=Decimal("500"),
                max_drawdown_percent=Decimal("0.10"),
                min_risk_reward_ratio=Decimal("2.0"),
                max_open_positions=5,
            )
        ),
    )

    signal = await engine.generate_signal(
        SignalRequest(
            symbol="BTCUSDT",
            timeframe="1h",
            strategy="positive_trend",
            account_equity=Decimal("10000"),
            current_exposure=Decimal("2000"),
            daily_loss=Decimal("50"),
            peak_equity=Decimal("10000"),
            current_equity=Decimal("9900"),
            open_positions=2,
        )
    )

    assert signal.signal == SignalValue.BUY
    assert signal.strategy == "positive_trend"
    assert signal.entry == Decimal("100")
    assert signal.stop_loss == Decimal("90")
    assert signal.take_profit == Decimal("120")


@pytest.mark.asyncio
async def test_signal_engine_holds_when_risk_rejects_trade() -> None:
    candles = [_make_candle("BTCUSDT", Decimal("99"), i) for i in range(1, 120)]
    analysis = TechnicalAnalysisResult(
        symbol="BTCUSDT",
        timeframe="1h",
        timestamp=candles[-1].timestamp,
        trend=TrendDirection.BULLISH,
        sma=SMAResult(period=20, value=Decimal("95")),
        ema=EMAResult(period=12, value=Decimal("97")),
        rsi=RSIResult(period=14, value=Decimal("60")),
        macd=MACDResult(
            fast_period=12,
            slow_period=26,
            signal_period=9,
            macd=Decimal("2.5"),
            signal=Decimal("1.0"),
            histogram=Decimal("1.5"),
        ),
        atr=ATRResult(period=14, value=Decimal("5")),
        strategies=[
            StrategyObservation(
                strategy_name="positive_trend",
                direction=TrendDirection.BULLISH,
                rationale="Trend is bullish.",
                indicator_values={"trend": "BULLISH"},
            )
        ],
    )

    engine = SignalEngine(
        market_data_service=FixedMarketDataService(price=Decimal("100"), candles=candles),
        technical_analysis_service=FixedTechnicalAnalysisService(analysis),
        strategy_registry=StrategyRegistry([PositiveTrendStrategy()]),
        risk_service=RiskManagementService(
            config=RiskConfiguration(
                max_portfolio_exposure=Decimal("1000"),
                max_daily_loss=Decimal("500"),
                max_drawdown_percent=Decimal("0.10"),
                min_risk_reward_ratio=Decimal("2.0"),
                max_open_positions=5,
            )
        ),
    )

    signal = await engine.generate_signal(
        SignalRequest(
            symbol="BTCUSDT",
            timeframe="1h",
            strategy="positive_trend",
            account_equity=Decimal("10000"),
            current_exposure=Decimal("2000"),
            daily_loss=Decimal("50"),
            peak_equity=Decimal("10000"),
            current_equity=Decimal("9900"),
            open_positions=2,
        )
    )

    assert signal.signal == SignalValue.HOLD
    assert "risk evaluation rejected" in signal.reasoning.lower()


@pytest.mark.asyncio
async def test_signal_engine_holds_on_neutral_strategy() -> None:
    candles = [_make_candle("BTCUSDT", Decimal("99"), i) for i in range(1, 120)]
    analysis = TechnicalAnalysisResult(
        symbol="BTCUSDT",
        timeframe="1h",
        timestamp=candles[-1].timestamp,
        trend=TrendDirection.NEUTRAL,
        sma=SMAResult(period=20, value=Decimal("100")),
        ema=EMAResult(period=12, value=Decimal("100")),
        rsi=RSIResult(period=14, value=Decimal("50")),
        macd=MACDResult(
            fast_period=12,
            slow_period=26,
            signal_period=9,
            macd=Decimal("0"),
            signal=Decimal("0"),
            histogram=Decimal("0"),
        ),
        atr=ATRResult(period=14, value=Decimal("5")),
        strategies=[
            StrategyObservation(
                strategy_name="positive_trend",
                direction=TrendDirection.NEUTRAL,
                rationale="Trend is neutral.",
                indicator_values={"trend": "NEUTRAL"},
            )
        ],
    )

    engine = SignalEngine(
        market_data_service=FixedMarketDataService(price=Decimal("100"), candles=candles),
        technical_analysis_service=FixedTechnicalAnalysisService(analysis),
        strategy_registry=StrategyRegistry([PositiveTrendStrategy()]),
        risk_service=RiskManagementService(config=RiskConfiguration()),
    )

    signal = await engine.generate_signal(
        SignalRequest(
            symbol="BTCUSDT",
            timeframe="1h",
            strategy="positive_trend",
            account_equity=Decimal("10000"),
            current_exposure=Decimal("2000"),
            daily_loss=Decimal("50"),
            peak_equity=Decimal("10000"),
            current_equity=Decimal("9900"),
            open_positions=2,
        )
    )

    assert signal.signal == SignalValue.HOLD
    assert "neutral trend" in signal.reasoning.lower()
