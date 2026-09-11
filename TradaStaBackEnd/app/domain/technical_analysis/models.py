"""Domain models for deterministic technical analysis."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum


class TrendDirection(Enum):
    """Simple deterministic trend direction used for analysis observations."""

    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"


@dataclass(frozen=True, slots=True)
class IndicatorConfig:
    """Configurable indicator periods for deterministic analysis."""

    sma_period: int = 20
    ema_period: int = 12
    rsi_period: int = 14
    macd_fast_period: int = 12
    macd_slow_period: int = 26
    macd_signal_period: int = 9
    bollinger_period: int = 20
    bollinger_stddev: int = 2
    atr_period: int = 14
    volume_period: int = 20

    def validate(self) -> None:
        """Validate the analysis configuration before use."""
        if self.sma_period <= 0:
            raise ValueError("sma_period must be greater than zero")
        if self.ema_period <= 0:
            raise ValueError("ema_period must be greater than zero")
        if self.rsi_period <= 0:
            raise ValueError("rsi_period must be greater than zero")
        if self.macd_fast_period <= 0:
            raise ValueError("macd_fast_period must be greater than zero")
        if self.macd_slow_period <= 0:
            raise ValueError("macd_slow_period must be greater than zero")
        if self.macd_signal_period <= 0:
            raise ValueError("macd_signal_period must be greater than zero")
        if self.macd_fast_period >= self.macd_slow_period:
            raise ValueError("macd_fast_period must be less than macd_slow_period")
        if self.bollinger_period <= 0:
            raise ValueError("bollinger_period must be greater than zero")
        if self.bollinger_stddev <= 0:
            raise ValueError("bollinger_stddev must be greater than zero")
        if self.atr_period <= 0:
            raise ValueError("atr_period must be greater than zero")
        if self.volume_period <= 0:
            raise ValueError("volume_period must be greater than zero")


@dataclass(frozen=True, slots=True)
class SMAResult:
    """Simple moving average result."""

    period: int
    value: Decimal


@dataclass(frozen=True, slots=True)
class EMAResult:
    """Exponential moving average result."""

    period: int
    value: Decimal


@dataclass(frozen=True, slots=True)
class RSIResult:
    """Relative Strength Index result."""

    period: int
    value: Decimal


@dataclass(frozen=True, slots=True)
class MACDResult:
    """MACD line, signal line, and histogram values."""

    fast_period: int
    slow_period: int
    signal_period: int
    macd: Decimal
    signal: Decimal
    histogram: Decimal


@dataclass(frozen=True, slots=True)
class BollingerBandsResult:
    """Upper/middle/lower Bollinger bands."""

    period: int
    stddev: Decimal
    upper: Decimal
    middle: Decimal
    lower: Decimal


@dataclass(frozen=True, slots=True)
class ATRResult:
    """Average True Range result."""

    period: int
    value: Decimal


@dataclass(frozen=True, slots=True)
class VolumeAnalysisResult:
    """Current and historical volume analysis."""

    period: int
    current_volume: Decimal
    average_volume: Decimal
    volume_ratio: Decimal


@dataclass(frozen=True, slots=True)
class StrategyObservation:
    """Deterministic strategy observation without trade-execution semantics."""

    strategy_name: str
    direction: TrendDirection
    rationale: str
    indicator_values: dict[str, Decimal | str | int] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class TechnicalAnalysisResult:
    """Deterministic technical-analysis output for a symbol and timeframe."""

    symbol: str
    timeframe: str
    timestamp: datetime
    trend: TrendDirection
    sma: SMAResult | None = None
    ema: EMAResult | None = None
    rsi: RSIResult | None = None
    macd: MACDResult | None = None
    bollinger_bands: BollingerBandsResult | None = None
    atr: ATRResult | None = None
    volume: VolumeAnalysisResult | None = None
    strategies: list[StrategyObservation] = field(default_factory=list)


__all__ = [
    "ATRResult",
    "BollingerBandsResult",
    "EMAResult",
    "IndicatorConfig",
    "MACDResult",
    "RSIResult",
    "SMAResult",
    "StrategyObservation",
    "TechnicalAnalysisResult",
    "TrendDirection",
    "VolumeAnalysisResult",
]
