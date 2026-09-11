"""Deterministic technical indicators built from normalized OHLCV candles."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from decimal import Decimal
from math import sqrt

from app.core.exceptions import (
    InsufficientMarketDataError,
    InvalidCandleError,
    InvalidIndicatorConfigurationError,
)
from app.domain.market_data import Candle
from app.domain.technical_analysis.models import (
    ATRResult,
    BollingerBandsResult,
    EMAResult,
    MACDResult,
    RSIResult,
    SMAResult,
    VolumeAnalysisResult,
)


def _sum(values: Iterable[Decimal]) -> Decimal:
    return sum(values, Decimal("0"))


def _ensure_period(period: int, value_name: str) -> None:
    if period <= 0:
        raise InvalidIndicatorConfigurationError(f"{value_name} must be greater than zero")


def _validate_candle_sequence(candles: Sequence[Candle]) -> None:
    if not candles:
        raise InsufficientMarketDataError("At least one candle is required for technical analysis")

    for candle in candles:
        if candle.high < candle.low:
            raise InvalidCandleError(
                f"Invalid OHLCV data for {candle.symbol}: high must be >= low"
            )
        if candle.high < max(candle.open, candle.close):
            raise InvalidCandleError(
                f"Invalid OHLCV data for {candle.symbol}: high is below open or close"
            )
        if candle.low > min(candle.open, candle.close):
            raise InvalidCandleError(
                f"Invalid OHLCV data for {candle.symbol}: low is above open or close"
            )
        if candle.volume < Decimal("0"):
            raise InvalidCandleError(
                f"Invalid OHLCV data for {candle.symbol}: volume must be non-negative"
            )

    ordered = sorted(candles, key=lambda item: item.timestamp)
    if ordered != list(candles):
        return


def sma(candles: Sequence[Candle], period: int = 20) -> SMAResult:
    """Return the simple moving average from the trailing period of closes."""
    _ensure_period(period, "period")
    if len(candles) < period:
        raise InsufficientMarketDataError(f"SMA requires at least {period} candles")

    trailing = candles[-period:]
    average = _sum(candle.close for candle in trailing) / Decimal(period)
    return SMAResult(period=period, value=average)


def ema(candles: Sequence[Candle], period: int = 12) -> EMAResult:
    """Return the exponential moving average using the first close as the seed value."""
    _ensure_period(period, "period")
    if len(candles) < period:
        raise InsufficientMarketDataError(f"EMA requires at least {period} candles")

    multiplier = Decimal(2) / Decimal(period + 1)
    result = candles[0].close
    for candle in candles[1:]:
        result = (candle.close - result) * multiplier + result
    return EMAResult(period=period, value=result)


def rsi(candles: Sequence[Candle], period: int = 14) -> RSIResult:
    """Return the Wilder RSI. A flat series resolves to 50, not an invalid value."""
    _ensure_period(period, "period")
    if len(candles) < period + 1:
        raise InsufficientMarketDataError(f"RSI requires at least {period + 1} candles")

    changes = [
        candles[index].close - candles[index - 1].close
        for index in range(1, len(candles))
    ]
    gains = [max(change, Decimal("0")) for change in changes[-period:]]
    losses = [max(-change, Decimal("0")) for change in changes[-period:]]

    avg_gain = _sum(gains) / Decimal(period)
    avg_loss = _sum(losses) / Decimal(period)

    if avg_loss == Decimal("0"):
        value = Decimal("100") if avg_gain > Decimal("0") else Decimal("50")
        return RSIResult(period=period, value=value)

    relative_strength = avg_gain / avg_loss
    value = Decimal("100") - (Decimal("100") / (Decimal("1") + relative_strength))
    return RSIResult(period=period, value=value)


def _ema_series(values: Sequence[Decimal], period: int) -> list[Decimal]:
    _ensure_period(period, "period")
    if not values:
        raise InsufficientMarketDataError("EMA requires at least one value")

    multiplier = Decimal(2) / Decimal(period + 1)
    result: list[Decimal] = []
    current = values[0]
    result.append(current)
    for value in values[1:]:
        current = (value - current) * multiplier + current
        result.append(current)
    return result


def macd(
    candles: Sequence[Candle],
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9,
) -> MACDResult:
    """Return MACD line, signal line, and histogram using EMA-based smoothing."""
    _ensure_period(fast_period, "fast_period")
    _ensure_period(slow_period, "slow_period")
    _ensure_period(signal_period, "signal_period")
    if fast_period >= slow_period:
        raise InvalidIndicatorConfigurationError(
            "fast_period must be lower than slow_period when calculating MACD"
        )
    if len(candles) < slow_period:
        raise InsufficientMarketDataError(f"MACD requires at least {slow_period} candles")

    closes = [candle.close for candle in candles]
    fast_ema = _ema_series(closes, fast_period)
    slow_ema = _ema_series(closes, slow_period)
    macd_values = [fast - slow for fast, slow in zip(fast_ema, slow_ema, strict=True)]
    if len(macd_values) < signal_period:
        raise InsufficientMarketDataError(
            f"MACD signal calculation requires at least {signal_period} MACD values"
        )

    signal_values = _ema_series(macd_values, signal_period)
    macd_value = macd_values[-1]
    signal_value = signal_values[-1]
    return MACDResult(
        fast_period=fast_period,
        slow_period=slow_period,
        signal_period=signal_period,
        macd=macd_value,
        signal=signal_value,
        histogram=macd_value - signal_value,
    )


def bollinger_bands(
    candles: Sequence[Candle],
    period: int = 20,
    stddev_multiplier: int = 2,
) -> BollingerBandsResult:
    """Return Bollinger Bands using population standard deviation across the trailing window."""
    _ensure_period(period, "period")
    _ensure_period(stddev_multiplier, "stddev_multiplier")
    if len(candles) < period:
        raise InsufficientMarketDataError(f"Bollinger Bands require at least {period} candles")

    trailing = candles[-period:]
    mean = _sum(candle.close for candle in trailing) / Decimal(period)
    variance = _sum((candle.close - mean) ** 2 for candle in trailing) / Decimal(period)
    stddev = Decimal(str(sqrt(float(variance))))
    upper = mean + Decimal(stddev_multiplier) * stddev
    lower = mean - Decimal(stddev_multiplier) * stddev
    return BollingerBandsResult(
        period=period,
        stddev=stddev,
        upper=upper,
        middle=mean,
        lower=lower,
    )


def atr(candles: Sequence[Candle], period: int = 14) -> ATRResult:
    """Return the Average True Range using Wilder's smoothing convention."""
    _ensure_period(period, "period")
    if len(candles) < period + 1:
        raise InsufficientMarketDataError(f"ATR requires at least {period + 1} candles")

    true_ranges: list[Decimal] = []
    for index in range(1, len(candles)):
        previous = candles[index - 1]
        current = candles[index]
        high_low = current.high - current.low
        high_prev_close = abs(current.high - previous.close)
        low_prev_close = abs(current.low - previous.close)
        true_ranges.append(max(high_low, high_prev_close, low_prev_close))

    first_atr = _sum(true_ranges[:period]) / Decimal(period)
    if len(true_ranges) == period:
        return ATRResult(period=period, value=first_atr)

    current_atr = first_atr
    for tr_value in true_ranges[period:]:
        current_atr = ((current_atr * Decimal(period - 1)) + tr_value) / Decimal(period)
    return ATRResult(period=period, value=current_atr)


def volume_analysis(
    candles: Sequence[Candle],
    period: int = 20,
) -> VolumeAnalysisResult:
    """Return current and average volume and a simple ratio metric."""
    _ensure_period(period, "period")
    if len(candles) < period:
        raise InsufficientMarketDataError(f"Volume analysis requires at least {period} candles")

    trailing = candles[-period:]
    current_volume = candles[-1].volume
    average_volume = _sum(candle.volume for candle in trailing) / Decimal(period)
    if average_volume == Decimal("0"):
        ratio = Decimal("0")
    else:
        ratio = current_volume / average_volume
    return VolumeAnalysisResult(
        period=period,
        current_volume=current_volume,
        average_volume=average_volume,
        volume_ratio=ratio,
    )


__all__ = [
    "ATRResult",
    "BollingerBandsResult",
    "EMAResult",
    "MACDResult",
    "RSIResult",
    "SMAResult",
    "VolumeAnalysisResult",
    "atr",
    "bollinger_bands",
    "ema",
    "macd",
    "rsi",
    "sma",
    "volume_analysis",
]
