"""Version 1 technical-analysis API endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict

from app.application.market_data_service import MarketDataService
from app.application.technical_analysis.service import TechnicalAnalysisService
from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.core.dependencies import market_data_service_dependency
from app.domain.technical_analysis.models import IndicatorConfig, TechnicalAnalysisResult

router = APIRouter(tags=["technical-analysis"])


class SMAResponse(BaseModel):
    period: int
    value: str


class EMAResponse(BaseModel):
    period: int
    value: str


class RSIResponse(BaseModel):
    period: int
    value: str


class MACDResponse(BaseModel):
    fast_period: int
    slow_period: int
    signal_period: int
    macd: str
    signal: str
    histogram: str


class BollingerBandsResponse(BaseModel):
    period: int
    stddev: str
    upper: str
    middle: str
    lower: str


class ATRResponse(BaseModel):
    period: int
    value: str


class VolumeAnalysisResponse(BaseModel):
    period: int
    current_volume: str
    average_volume: str
    volume_ratio: str


class IndicatorSummary(BaseModel):
    sma: SMAResponse | None = None
    ema: EMAResponse | None = None
    rsi: RSIResponse | None = None
    macd: MACDResponse | None = None
    bollinger_bands: BollingerBandsResponse | None = None
    atr: ATRResponse | None = None
    volume: VolumeAnalysisResponse | None = None


class StrategyResponse(BaseModel):
    strategy_name: str
    direction: str
    rationale: str
    indicator_values: dict[str, str | int]


class TechnicalAnalysisResponse(BaseModel):
    symbol: str
    timeframe: str
    timestamp: datetime
    trend: str
    indicators: IndicatorSummary
    strategies: list[StrategyResponse] = []

    model_config = ConfigDict(use_enum_values=True)

    @staticmethod
    def from_result(result: TechnicalAnalysisResult) -> TechnicalAnalysisResponse:
        sma_result = (
            SMAResponse(period=result.sma.period, value=str(result.sma.value))
            if result.sma is not None
            else None
        )
        ema_result = (
            EMAResponse(period=result.ema.period, value=str(result.ema.value))
            if result.ema is not None
            else None
        )
        rsi_result = (
            RSIResponse(period=result.rsi.period, value=str(result.rsi.value))
            if result.rsi is not None
            else None
        )
        macd_result = (
            MACDResponse(
                fast_period=result.macd.fast_period,
                slow_period=result.macd.slow_period,
                signal_period=result.macd.signal_period,
                macd=str(result.macd.macd),
                signal=str(result.macd.signal),
                histogram=str(result.macd.histogram),
            )
            if result.macd is not None
            else None
        )
        bollinger_result = (
            BollingerBandsResponse(
                period=result.bollinger_bands.period,
                stddev=str(result.bollinger_bands.stddev),
                upper=str(result.bollinger_bands.upper),
                middle=str(result.bollinger_bands.middle),
                lower=str(result.bollinger_bands.lower),
            )
            if result.bollinger_bands is not None
            else None
        )
        atr_result = (
            ATRResponse(period=result.atr.period, value=str(result.atr.value))
            if result.atr is not None
            else None
        )
        volume_result = (
            VolumeAnalysisResponse(
                period=result.volume.period,
                current_volume=str(result.volume.current_volume),
                average_volume=str(result.volume.average_volume),
                volume_ratio=str(result.volume.volume_ratio),
            )
            if result.volume is not None
            else None
        )

        return TechnicalAnalysisResponse(
            symbol=result.symbol,
            timeframe=result.timeframe,
            timestamp=result.timestamp,
            trend=result.trend.value,
            indicators=IndicatorSummary(
                sma=sma_result,
                ema=ema_result,
                rsi=rsi_result,
                macd=macd_result,
                bollinger_bands=bollinger_result,
                atr=atr_result,
                volume=volume_result,
            ),
            strategies=[
                StrategyResponse(
                    strategy_name=item.strategy_name,
                    direction=item.direction.value,
                    rationale=item.rationale,
                    indicator_values={
                        key: str(value) if not isinstance(value, int) else value
                        for key, value in item.indicator_values.items()
                    },
                )
                for item in result.strategies
            ],
        )


@router.get("/analysis/{symbol}")
async def get_technical_analysis(
    symbol: str,
    timeframe: str = Query(default="1h", min_length=1),
    limit: int = Query(default=200, ge=20, le=500),
    sma_period: int = Query(default=20, ge=1),
    ema_period: int = Query(default=12, ge=1),
    rsi_period: int = Query(default=14, ge=1),
    macd_fast_period: int = Query(default=12, ge=1),
    macd_slow_period: int = Query(default=26, ge=1),
    macd_signal_period: int = Query(default=9, ge=1),
    bollinger_period: int = Query(default=20, ge=1),
    bollinger_stddev: int = Query(default=2, ge=1),
    atr_period: int = Query(default=14, ge=1),
    volume_period: int = Query(default=20, ge=1),
    *,
    market_data_service: Annotated[
        MarketDataService, Depends(market_data_service_dependency)
    ],
    current_user: Annotated[User | None, Depends(get_current_user)] = None,
) -> TechnicalAnalysisResponse:
    """Run deterministic technical indicators and return a provider-independent analysis payload."""
    candles = await market_data_service.get_ohlcv(symbol, timeframe=timeframe, limit=limit)
    config = IndicatorConfig(
        sma_period=sma_period,
        ema_period=ema_period,
        rsi_period=rsi_period,
        macd_fast_period=macd_fast_period,
        macd_slow_period=macd_slow_period,
        macd_signal_period=macd_signal_period,
        bollinger_period=bollinger_period,
        bollinger_stddev=bollinger_stddev,
        atr_period=atr_period,
        volume_period=volume_period,
    )
    analysis = TechnicalAnalysisService(config=config).analyze(
        candles, symbol=symbol, timeframe=timeframe
    )
    return TechnicalAnalysisResponse.from_result(analysis)


__all__ = ["TechnicalAnalysisResponse", "router"]
