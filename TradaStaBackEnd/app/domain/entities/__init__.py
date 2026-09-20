"""Domain entity definitions used by the application layer."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID


@dataclass(slots=True)
class User:
    """User domain entity."""

    id: UUID
    email: str
    username: str
    is_active: bool = True
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass(slots=True)
class Asset:
    """Asset domain entity."""

    id: UUID
    symbol: str
    name: str
    asset_type: str = "crypto"
    is_active: bool = True
    created_at: datetime | None = None
    updated_at: datetime | None = None


class SignalValue(StrEnum):
    """Final deterministic signal value."""

    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


@dataclass(slots=True)
class TradingSignal:
    """Trading signal domain entity."""

    signal: SignalValue
    symbol: str
    price: Decimal | None = None
    indicators: dict[str, str] = field(default_factory=dict)
    strategy: str = "moving_average_trend"
    confidence: Decimal = Decimal("0")
    entry: Decimal | None = None
    stop_loss: Decimal | None = None
    take_profit: Decimal | None = None
    risk_reward_ratio: Decimal | None = None
    reasoning: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def signal_type(self) -> SignalValue:
        """Backward-compatible alias for the signal value."""
        return self.signal
