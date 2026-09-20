"""Version 1 market-data API endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict

from app.application.market_data_service import MarketDataService
from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.core.dependencies import market_data_service_dependency
from app.domain.market_data import Candle

router = APIRouter(tags=["market-data"])


class MarketPriceResponse(BaseModel):
    """Provider-independent current-market-price response."""

    symbol: str
    price: str
    currency: str
    timestamp: datetime

    model_config = ConfigDict(
        json_schema_extra={
            "example": {"symbol": "BTC", "price": "65500.12", "currency": "USD"}
        }
    )


class MarketCandleResponse(BaseModel):
    """Provider-independent OHLCV candle response."""

    symbol: str
    timestamp: datetime
    open: str
    high: str
    low: str
    close: str
    volume: str

    @staticmethod
    def from_candle(candle: Candle) -> MarketCandleResponse:
        return MarketCandleResponse(
            symbol=candle.symbol,
            timestamp=candle.timestamp,
            open=str(candle.open),
            high=str(candle.high),
            low=str(candle.low),
            close=str(candle.close),
            volume=str(candle.volume),
        )


class MarketOHLCVResponse(BaseModel):
    """A market-data payload containing candles."""

    symbol: str
    timeframe: str
    candles: list[MarketCandleResponse]


@router.get("/market-data/{symbol}/price")
async def get_market_price(
    symbol: str,
    market_data_service: Annotated[
        MarketDataService, Depends(market_data_service_dependency)
    ],
    current_user: Annotated[User | None, Depends(get_current_user)] = None,
) -> MarketPriceResponse:
    """Return the latest market price for a symbol without provider-specific models."""
    price = await market_data_service.get_current_price(symbol)
    return MarketPriceResponse(
        symbol=price.symbol,
        price=str(price.price),
        currency=price.currency,
        timestamp=price.timestamp,
    )


@router.get("/market-data/{symbol}/ohlcv")
async def get_market_ohlcv(
    symbol: str,
    timeframe: str = Query(default="1h", min_length=1),
    limit: int = Query(default=24, ge=1, le=500),
    *,
    market_data_service: Annotated[
        MarketDataService, Depends(market_data_service_dependency)
    ],
    current_user: Annotated[User | None, Depends(get_current_user)] = None,
) -> MarketOHLCVResponse:
    """Return a normalized OHLCV series for the requested symbol and timeframe."""
    candles = await market_data_service.get_ohlcv(symbol, timeframe=timeframe, limit=limit)
    return MarketOHLCVResponse(
        symbol=symbol.upper(),
        timeframe=timeframe,
        candles=[MarketCandleResponse.from_candle(candle) for candle in candles],
    )


__all__ = ["MarketCandleResponse", "MarketOHLCVResponse", "MarketPriceResponse", "router"]
