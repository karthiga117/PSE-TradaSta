"""Domain models for deterministic risk management."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from enum import StrEnum


def _as_decimal(value: object | None, *, field_name: str) -> Decimal:
    """Convert supported numeric inputs to Decimal while preserving explicit validation."""
    if value is None:
        raise ValueError(f"{field_name} is required")
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:  # pragma: no cover - defensive
        raise ValueError(f"{field_name} must be a valid decimal value") from exc


class RiskDirection(StrEnum):
    """Explicit trade direction for risk validation."""

    LONG = "LONG"
    SHORT = "SHORT"


class RiskDecisionReason(StrEnum):
    """Stable machine-readable risk decision reasons."""

    APPROVED = "APPROVED"
    INVALID_INPUT = "INVALID_INPUT"
    RISK_LIMIT_EXCEEDED = "RISK_LIMIT_EXCEEDED"
    POSITION_SIZE_EXCEEDED = "POSITION_SIZE_EXCEEDED"
    PORTFOLIO_EXPOSURE_EXCEEDED = "PORTFOLIO_EXPOSURE_EXCEEDED"
    DAILY_LOSS_LIMIT_EXCEEDED = "DAILY_LOSS_LIMIT_EXCEEDED"
    DRAWDOWN_LIMIT_EXCEEDED = "DRAWDOWN_LIMIT_EXCEEDED"
    OPEN_POSITION_LIMIT_EXCEEDED = "OPEN_POSITION_LIMIT_EXCEEDED"
    INVALID_STOP_LOSS = "INVALID_STOP_LOSS"
    INVALID_TAKE_PROFIT = "INVALID_TAKE_PROFIT"
    INSUFFICIENT_RISK_REWARD = "INSUFFICIENT_RISK_REWARD"


@dataclass(frozen=True, slots=True)
class RiskConfiguration:
    """Risk policy configuration used by the deterministic Risk Engine."""

    risk_per_trade_percent: Decimal = Decimal("0.01")
    max_risk_per_trade: Decimal | None = None
    max_position_size: Decimal = Decimal("1000000")
    max_portfolio_exposure: Decimal = Decimal("50000")
    max_daily_loss: Decimal = Decimal("500")
    max_drawdown_percent: Decimal = Decimal("0.10")
    min_risk_reward_ratio: Decimal = Decimal("2.0")
    max_open_positions: int = 5
    stop_loss_required: bool = True
    take_profit_required: bool = True

    def validate(self) -> None:
        """Validate the policy configuration before evaluating a trade."""
        if self.risk_per_trade_percent <= 0:
            raise ValueError("risk_per_trade_percent must be greater than zero")
        if self.max_risk_per_trade is not None and self.max_risk_per_trade <= 0:
            raise ValueError("max_risk_per_trade must be greater than zero when provided")
        if self.max_position_size <= 0:
            raise ValueError("max_position_size must be greater than zero")
        if self.max_portfolio_exposure <= 0:
            raise ValueError("max_portfolio_exposure must be greater than zero")
        if self.max_daily_loss <= 0:
            raise ValueError("max_daily_loss must be greater than zero")
        if self.max_drawdown_percent <= 0 or self.max_drawdown_percent >= 1:
            raise ValueError("max_drawdown_percent must be between 0 and 1")
        if self.min_risk_reward_ratio <= 0:
            raise ValueError("min_risk_reward_ratio must be greater than zero")
        if self.max_open_positions <= 0:
            raise ValueError("max_open_positions must be greater than zero")


@dataclass(frozen=True, slots=True)
class RiskRequest:
    """Proposed trade details submitted to the risk engine."""

    symbol: str
    side: RiskDirection | str
    entry_price: Decimal
    stop_loss: Decimal | None = None
    take_profit: Decimal | None = None
    account_equity: Decimal | None = None
    current_exposure: Decimal | None = None
    daily_loss: Decimal | None = None
    peak_equity: Decimal | None = None
    current_equity: Decimal | None = None
    open_positions: int | None = None

    @classmethod
    def from_mapping(cls, values: dict[str, object]) -> RiskRequest:
        """Coerce request payload values into the expected domain types."""
        side_value = values.get("side")
        if isinstance(side_value, RiskDirection):
            side = side_value
        else:
            side = RiskDirection(str(side_value).upper())
        return cls(
            symbol=str(values.get("symbol") or "").strip(),
            side=side,
            entry_price=_as_decimal(values.get("entry_price"), field_name="entry_price"),
            stop_loss=(
                _as_decimal(values["stop_loss"], field_name="stop_loss")
                if values.get("stop_loss") is not None
                else None
            ),
            take_profit=(
                _as_decimal(values["take_profit"], field_name="take_profit")
                if values.get("take_profit") is not None
                else None
            ),
            account_equity=(
                _as_decimal(values["account_equity"], field_name="account_equity")
                if values.get("account_equity") is not None
                else None
            ),
            current_exposure=(
                _as_decimal(values["current_exposure"], field_name="current_exposure")
                if values.get("current_exposure") is not None
                else None
            ),
            daily_loss=(
                _as_decimal(values["daily_loss"], field_name="daily_loss")
                if values.get("daily_loss") is not None
                else None
            ),
            peak_equity=(
                _as_decimal(values["peak_equity"], field_name="peak_equity")
                if values.get("peak_equity") is not None
                else None
            ),
            current_equity=(
                _as_decimal(values["current_equity"], field_name="current_equity")
                if values.get("current_equity") is not None
                else None
            ),
            open_positions=(
                int(str(values["open_positions"]))
                if values.get("open_positions") is not None
                else None
            ),
        )

    def risk_distance(self) -> Decimal:
        """Distance between entry price and stop loss, expressed as a positive Decimal."""
        if self.stop_loss is None:
            raise ValueError("stop_loss is required to calculate risk distance")
        return abs(self.entry_price - self.stop_loss)

    def direction(self) -> RiskDirection:
        """Normalize side to a RiskDirection enum."""
        if isinstance(self.side, RiskDirection):
            return self.side
        return RiskDirection(str(self.side).upper())


@dataclass(frozen=True, slots=True)
class PositionSize:
    """Deterministic position size and exposure metadata."""

    risk_amount: Decimal
    position_size: Decimal
    risk_distance: Decimal
    proposed_exposure: Decimal


@dataclass(frozen=True, slots=True)
class RiskMetrics:
    """Calculated risk metrics for a single proposed trade."""

    risk_amount: Decimal
    position_size: Decimal
    risk_reward_ratio: Decimal
    proposed_exposure: Decimal
    drawdown_percent: Decimal | None = None


@dataclass(frozen=True, slots=True)
class PortfolioExposure:
    """Current and proposed portfolio exposure details."""

    current_exposure: Decimal
    proposed_exposure: Decimal
    total_exposure: Decimal
    max_portfolio_exposure: Decimal


@dataclass(frozen=True, slots=True)
class RiskContext:
    """A fully materialized evaluation context for risk rules."""

    request: RiskRequest
    config: RiskConfiguration
    risk_amount: Decimal
    position_size: Decimal
    risk_reward_ratio: Decimal
    proposed_exposure: Decimal
    portfolio_exposure: PortfolioExposure
    drawdown_percent: Decimal | None
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class RiskDecision:
    """Outcome of a deterministic risk evaluation."""

    approved: bool
    reason_code: str
    reason: str
    risk_amount: Decimal | None = None
    position_size: Decimal | None = None
    risk_reward_ratio: Decimal | None = None
    portfolio_exposure: Decimal | None = None
    warnings: list[str] = field(default_factory=list)
    evaluated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


__all__ = [
    "PortfolioExposure",
    "PositionSize",
    "RiskConfiguration",
    "RiskContext",
    "RiskDecision",
    "RiskDecisionReason",
    "RiskDirection",
    "RiskMetrics",
    "RiskRequest",
]
