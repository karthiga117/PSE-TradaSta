"""Domain models for market data."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal


def _utc_now() -> datetime:
    """Return the current UTC timestamp."""
    return datetime.now(UTC)


def _coerce_decimal(value: object, field_name: str) -> Decimal:
    """Coerce a value to Decimal without leaking floats into domain code."""
    if value is None or value == "":
        raise ValueError(f"{field_name} is required")

    try:
        return Decimal(str(value))
    except (ArithmeticError, TypeError, ValueError) as exc:  # pragma: no cover - defensive
        raise ValueError(f"{field_name} must be numeric") from exc


@dataclass(frozen=True, slots=True)
class MarketPrice:
    """Represents the current price for a traded symbol."""

    symbol: str
    price: Decimal
    currency: str = "USD"
    timestamp: datetime = field(default_factory=_utc_now)
    source: str = "market_data_service"

    @classmethod
    def from_value(
        cls,
        symbol: str,
        value: Decimal | int | float | str,
        *,
        currency: str = "USD",
        timestamp: datetime | None = None,
        source: str = "market_data_service",
    ) -> MarketPrice:
        """Create a price object from a numeric value."""
        return cls(
            symbol=symbol.upper(),
            price=_coerce_decimal(value, "price"),
            currency=currency.upper(),
            timestamp=timestamp or _utc_now(),
            source=source,
        )


@dataclass(frozen=True, slots=True)
class Candle:
    """Represents an OHLCV candle for a market symbol."""

    symbol: str
    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal

    @classmethod
    def from_values(
        cls,
        symbol: str,
        timestamp: datetime,
        open_price: Decimal | int | float | str,
        high_price: Decimal | int | float | str,
        low_price: Decimal | int | float | str,
        close_price: Decimal | int | float | str,
        volume: Decimal | int | float | str,
    ) -> Candle:
        """Create a candle from raw numeric values."""
        return cls(
            symbol=symbol.upper(),
            timestamp=timestamp,
            open=_coerce_decimal(open_price, "open"),
            high=_coerce_decimal(high_price, "high"),
            low=_coerce_decimal(low_price, "low"),
            close=_coerce_decimal(close_price, "close"),
            volume=_coerce_decimal(volume, "volume"),
        )


@dataclass(frozen=True, slots=True)
class MarketSnapshot:
    """Aggregated snapshot for a symbol at a point in time."""

    symbol: str
    price: Decimal
    timestamp: datetime = field(default_factory=_utc_now)
    volume_24h: Decimal | None = None
    market_cap: Decimal | None = None


__all__ = ["Candle", "MarketPrice", "MarketSnapshot"]
