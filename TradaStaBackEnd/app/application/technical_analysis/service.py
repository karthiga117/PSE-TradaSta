"""Technical analysis application service."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from app.application.technical_analysis.strategies import build_default_registry
from app.core.exceptions import InsufficientMarketDataError, InvalidCandleError
from app.domain.market_data import Candle
from app.domain.technical_analysis.indicators import (
    atr,
    bollinger_bands,
    ema,
    macd,
    rsi,
    sma,
    volume_analysis,
)
from app.domain.technical_analysis.models import (
    IndicatorConfig,
    TechnicalAnalysisResult,
    TrendDirection,
)


class TechnicalAnalysisService:
    """Validate and calculate deterministic technical-analysis results."""

    def __init__(self, config: IndicatorConfig | None = None) -> None:
        self.config = config or IndicatorConfig()
        self.config.validate()
        self._registry = build_default_registry()

    def analyze(
        self,
        candles: Sequence[Candle],
        *,
        symbol: str,
        timeframe: str = "1h",
    ) -> TechnicalAnalysisResult:
        """Return composite technical analysis for the provided candle history."""
        if not candles:
            raise InsufficientMarketDataError("Technical analysis requires at least one candle")

        normalized = self._normalize_candles(list(candles))
        minimum_required = max(
            self.config.sma_period,
            self.config.ema_period,
            self.config.rsi_period + 1,
            self.config.macd_slow_period,
            self.config.bollinger_period,
            self.config.atr_period + 1,
            self.config.volume_period,
        )
        if len(normalized) < minimum_required:
            raise InsufficientMarketDataError(
                "Insufficient candles for the configured technical-analysis thresholds"
            )

        sma_result = sma(normalized, self.config.sma_period)
        ema_result = ema(normalized, self.config.ema_period)
        rsi_result = rsi(normalized, self.config.rsi_period)
        macd_result = macd(
            normalized,
            fast_period=self.config.macd_fast_period,
            slow_period=self.config.macd_slow_period,
            signal_period=self.config.macd_signal_period,
        )
        bollinger_result = bollinger_bands(
            normalized,
            period=self.config.bollinger_period,
            stddev_multiplier=self.config.bollinger_stddev,
        )
        atr_result = atr(normalized, period=self.config.atr_period)
        volume_result = volume_analysis(normalized, period=self.config.volume_period)
        trend = self._detect_trend(normalized)

        analysis = TechnicalAnalysisResult(
            symbol=symbol,
            timeframe=timeframe,
            timestamp=normalized[-1].timestamp,
            trend=trend,
            sma=sma_result,
            ema=ema_result,
            rsi=rsi_result,
            macd=macd_result,
            bollinger_bands=bollinger_result,
            atr=atr_result,
            volume=volume_result,
            strategies=[],
        )
        analysis = TechnicalAnalysisResult(
            symbol=analysis.symbol,
            timeframe=analysis.timeframe,
            timestamp=analysis.timestamp,
            trend=analysis.trend,
            sma=analysis.sma,
            ema=analysis.ema,
            rsi=analysis.rsi,
            macd=analysis.macd,
            bollinger_bands=analysis.bollinger_bands,
            atr=analysis.atr,
            volume=analysis.volume,
            strategies=[strategy.evaluate(analysis) for strategy in self._registry.all()],
        )
        return analysis

    def _detect_trend(self, candles: Sequence[Candle]) -> TrendDirection:
        """Use a simple moving-average and EMA relationship to classify trend."""
        current_close = candles[-1].close
        sma_value = sma(candles, self.config.sma_period).value
        ema_value = ema(candles, self.config.ema_period).value

        if current_close > sma_value and current_close > ema_value:
            return TrendDirection.BULLISH
        if current_close < sma_value and current_close < ema_value:
            return TrendDirection.BEARISH
        return TrendDirection.NEUTRAL

    @staticmethod
    def _normalize_candles(candles: list[Candle]) -> list[Candle]:
        """Normalize candle ordering while guarding against invalid OHLCV data."""
        normalized = sorted(candles, key=lambda candle: candle.timestamp)
        seen: set[datetime] = set()
        for candle in normalized:
            if candle.high < candle.low:
                raise InvalidCandleError(f"Invalid OHLCV for {candle.symbol}: high < low")
            if candle.high < max(candle.open, candle.close):
                raise InvalidCandleError(
                    f"Invalid OHLCV for {candle.symbol}: high does not exceed open/close"
                )
            if candle.low > min(candle.open, candle.close):
                raise InvalidCandleError(
                    f"Invalid OHLCV for {candle.symbol}: low does not stay below open/close"
                )
            if candle.volume < 0:
                raise InvalidCandleError(f"Invalid OHLCV for {candle.symbol}: negative volume")
            if candle.timestamp in seen:
                raise InvalidCandleError(f"Duplicate timestamp detected for {candle.symbol}")
            seen.add(candle.timestamp)
        return normalized


__all__ = ["TechnicalAnalysisService"]
