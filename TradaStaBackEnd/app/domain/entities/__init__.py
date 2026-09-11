"""Domain entity definitions used by the application layer."""

from dataclasses import dataclass
from datetime import datetime
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


@dataclass(slots=True)
class TradingSignal:
    """Trading signal domain entity."""

    id: UUID
    asset_id: UUID
    strategy_id: UUID
    signal_type: str
    confidence: float
    strength: float
    created_at: datetime | None = None
