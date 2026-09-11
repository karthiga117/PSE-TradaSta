"""Trading signal API endpoints."""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field

from app.application.signal_engine import SignalEngine
from app.core.dependencies import signal_engine_dependency
from app.domain.signal import SignalRequest, TradingSignal

router = APIRouter(tags=["signals"])


def format_decimal(value: Decimal | None) -> str | None:
    """Render a Decimal in a stable string form for API responses."""
    if value is None:
        return None
    return str(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


class SignalRequestPayload(BaseModel):
    """Inbound request model for signal generation."""

    symbol: str
    timeframe: str = "1h"
    strategy: str | None = None
    account_equity: Decimal | None = None
    current_exposure: Decimal | None = None
    daily_loss: Decimal | None = None
    peak_equity: Decimal | None = None
    current_equity: Decimal | None = None
    open_positions: int | None = None
    strategy_parameters: dict[str, Any] = Field(default_factory=dict)
    risk_configuration_overrides: dict[str, Any] = Field(default_factory=dict)


class SignalResponse(BaseModel):
    """Stable response model for trading signals."""

    signal: str
    symbol: str
    price: str | None = None
    indicators: dict[str, str] = Field(default_factory=dict)
    strategy: str
    confidence: str
    entry: str | None = None
    stop_loss: str | None = None
    take_profit: str | None = None
    risk_reward: str | None = None
    risk_reward_ratio: str | None = None
    reasoning: str
    timestamp: str
    model_config = ConfigDict(use_enum_values=True)

    @staticmethod
    def from_signal(signal: TradingSignal) -> SignalResponse:
        confidence_value = format_decimal(signal.confidence) or "0.00"
        return SignalResponse(
            signal=signal.signal.value,
            symbol=signal.symbol,
            price=format_decimal(signal.price),
            indicators=signal.indicators,
            strategy=signal.strategy,
            confidence=confidence_value,
            entry=format_decimal(signal.entry),
            stop_loss=format_decimal(signal.stop_loss),
            take_profit=format_decimal(signal.take_profit),
            risk_reward=format_decimal(signal.risk_reward_ratio),
            risk_reward_ratio=format_decimal(signal.risk_reward_ratio),
            reasoning=signal.reasoning,
            timestamp=signal.timestamp.isoformat(),
        )


@router.post("/signals")
async def generate_signal(
    payload: SignalRequestPayload,
    signal_engine: Annotated[SignalEngine, Depends(signal_engine_dependency)],
) -> SignalResponse:
    """Generate a deterministic trading signal using the configured orchestration stack."""
    request = SignalRequest.from_mapping(payload.model_dump())
    signal = await signal_engine.generate_signal(request)
    return SignalResponse.from_signal(signal)


__all__ = ["SignalRequestPayload", "SignalResponse", "router"]
