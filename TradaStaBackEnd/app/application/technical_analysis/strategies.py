"""Deterministic technical-analysis strategies."""

from __future__ import annotations

from abc import ABC, abstractmethod
from decimal import Decimal

from app.domain.technical_analysis.models import (
    StrategyObservation,
    TechnicalAnalysisResult,
    TrendDirection,
)


class TechnicalStrategy(ABC):
    """Strategy abstraction for deterministic analysis observations."""

    name: str

    @abstractmethod
    def evaluate(self, result: TechnicalAnalysisResult) -> StrategyObservation:
        """Return a deterministic observation derived from technical-analysis output."""


class MovingAverageTrendStrategy(TechnicalStrategy):
    """A moving-average trend observation without final trading recommendations."""

    name = "moving_average_trend"

    def __init__(self, fast_period: int = 20, slow_period: int = 50) -> None:
        self.fast_period = fast_period
        self.slow_period = slow_period

    def evaluate(self, result: TechnicalAnalysisResult) -> StrategyObservation:
        if result.sma is None:
            raise ValueError("MovingAverageTrendStrategy requires SMA values")
        if result.ema is None:
            raise ValueError("MovingAverageTrendStrategy requires EMA values")

        fast_value = result.sma.value
        slow_value = result.ema.value
        if fast_value > slow_value:
            direction = TrendDirection.BULLISH
            rationale = f"Fast SMA {fast_value} is above EMA {slow_value}"
        elif fast_value < slow_value:
            direction = TrendDirection.BEARISH
            rationale = f"Fast SMA {fast_value} is below EMA {slow_value}"
        else:
            direction = TrendDirection.NEUTRAL
            rationale = f"Fast SMA {fast_value} is equal to EMA {slow_value}"

        return StrategyObservation(
            strategy_name=self.name,
            direction=direction,
            rationale=rationale,
            indicator_values={"sma": fast_value, "ema": slow_value},
        )


class RSIStrategy(TechnicalStrategy):
    """A simple RSI threshold strategy used for technical observations only."""

    name = "rsi"

    def __init__(self, lower_threshold: int = 30, upper_threshold: int = 70) -> None:
        self.lower_threshold = lower_threshold
        self.upper_threshold = upper_threshold

    def evaluate(self, result: TechnicalAnalysisResult) -> StrategyObservation:
        if result.rsi is None:
            raise ValueError("RSIStrategy requires RSI values")

        rsi_value = result.rsi.value
        if rsi_value < Decimal(str(self.lower_threshold)):
            direction = TrendDirection.BEARISH
            rationale = f"RSI {rsi_value} is below the lower threshold {self.lower_threshold}"
        elif rsi_value > Decimal(str(self.upper_threshold)):
            direction = TrendDirection.BULLISH
            rationale = f"RSI {rsi_value} is above the upper threshold {self.upper_threshold}"
        else:
            direction = TrendDirection.NEUTRAL
            rationale = f"RSI {rsi_value} is within the neutral band"

        return StrategyObservation(
            strategy_name=self.name,
            direction=direction,
            rationale=rationale,
            indicator_values={"rsi": rsi_value},
        )


class MACDStrategy(TechnicalStrategy):
    """A MACD momentum observation without final trade recommendations."""

    name = "macd"

    def __init__(self, zero_line_threshold: Decimal | float | int = 0) -> None:
        self.zero_line_threshold = Decimal(str(zero_line_threshold))

    def evaluate(self, result: TechnicalAnalysisResult) -> StrategyObservation:
        if result.macd is None:
            raise ValueError("MACDStrategy requires MACD values")

        macd_value = result.macd.macd
        signal_value = result.macd.signal
        if macd_value > signal_value + self.zero_line_threshold:
            direction = TrendDirection.BULLISH
            rationale = f"MACD {macd_value} is above signal {signal_value}"
        elif macd_value < signal_value - self.zero_line_threshold:
            direction = TrendDirection.BEARISH
            rationale = f"MACD {macd_value} is below signal {signal_value}"
        else:
            direction = TrendDirection.NEUTRAL
            rationale = f"MACD {macd_value} is near the signal line {signal_value}"

        return StrategyObservation(
            strategy_name=self.name,
            direction=direction,
            rationale=rationale,
            indicator_values={"macd": macd_value, "signal": signal_value},
        )


class StrategyRegistry:
    """Simple dependency-injected strategy registry."""

    def __init__(self, strategies: list[TechnicalStrategy] | None = None) -> None:
        self._strategies = {strategy.name: strategy for strategy in (strategies or [])}

    def register(self, strategy: TechnicalStrategy) -> None:
        self._strategies[strategy.name] = strategy

    def get(self, name: str) -> TechnicalStrategy:
        try:
            return self._strategies[name]
        except KeyError as exc:
            raise KeyError(f"Unknown strategy: {name}") from exc

    def all(self) -> list[TechnicalStrategy]:
        return list(self._strategies.values())


def build_default_registry() -> StrategyRegistry:
    """Return the default strategy registry for the technical-analysis service."""
    return StrategyRegistry(
        [
            MovingAverageTrendStrategy(),
            RSIStrategy(),
            MACDStrategy(),
        ]
    )


__all__ = [
    "MACDStrategy",
    "MovingAverageTrendStrategy",
    "RSIStrategy",
    "StrategyRegistry",
    "TechnicalStrategy",
    "build_default_registry",
]
