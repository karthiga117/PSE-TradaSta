"""Deterministic risk-management service and rule set."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation

from app.domain.risk_management.models import (
    PortfolioExposure,
    RiskConfiguration,
    RiskContext,
    RiskDecision,
    RiskDecisionReason,
    RiskDirection,
    RiskRequest,
)


class RiskRule(ABC):
    """Composable rule used to evaluate a trade request."""

    @abstractmethod
    def evaluate(self, context: RiskContext) -> RiskDecision | None:
        """Return a decision when the rule rejects a trade, otherwise None."""


class InputValidationRule(RiskRule):
    """Validate basic trade and account input before any risk math is evaluated."""

    def evaluate(self, context: RiskContext) -> RiskDecision | None:
        request = context.request
        if not request.symbol or not request.symbol.strip():
            return self._reject(
                reason_code=RiskDecisionReason.INVALID_INPUT,
                reason="symbol is required for risk evaluation.",
            )
        if request.direction() not in (RiskDirection.LONG, RiskDirection.SHORT):
            return self._reject(
                reason_code=RiskDecisionReason.INVALID_INPUT,
                reason="side must be either LONG or SHORT.",
            )
        if request.account_equity is None or request.account_equity <= 0:
            return self._reject(
                reason_code=RiskDecisionReason.INVALID_INPUT,
                reason="account_equity must be greater than zero.",
            )
        if request.entry_price <= 0:
            return self._reject(
                reason_code=RiskDecisionReason.INVALID_INPUT,
                reason="entry_price must be greater than zero.",
            )
        if request.current_exposure is None and context.config.max_portfolio_exposure > 0:
            return self._reject(
                reason_code=RiskDecisionReason.INVALID_INPUT,
                reason="current_exposure is required for portfolio exposure validation.",
            )
        if request.current_equity is None and context.config.max_drawdown_percent > 0:
            return self._reject(
                reason_code=RiskDecisionReason.INVALID_INPUT,
                reason="current_equity is required for drawdown validation.",
            )
        if request.peak_equity is None and context.config.max_drawdown_percent > 0:
            return self._reject(
                reason_code=RiskDecisionReason.INVALID_INPUT,
                reason="peak_equity is required for drawdown validation.",
            )
        if request.daily_loss is None:
            return self._reject(
                reason_code=RiskDecisionReason.INVALID_INPUT,
                reason="daily_loss is required for daily-loss validation.",
            )
        if request.open_positions is None:
            return self._reject(
                reason_code=RiskDecisionReason.INVALID_INPUT,
                reason="open_positions is required for open-position validation.",
            )
        return None

    @staticmethod
    def _reject(*, reason_code: RiskDecisionReason, reason: str) -> RiskDecision:
        return RiskDecision(
            approved=False,
            reason_code=reason_code.value,
            reason=reason,
            warnings=[],
            evaluated_at=datetime.now(UTC),
        )


class StopLossRule(RiskRule):
    """Validate stop-loss placement for both long and short trades."""

    def evaluate(self, context: RiskContext) -> RiskDecision | None:
        request = context.request
        if request.stop_loss is None:
            if context.config.stop_loss_required:
                return self._reject(
                    reason_code=RiskDecisionReason.INVALID_STOP_LOSS,
                    reason="A valid stop loss is required for this trade.",
                )
            return None

        if request.stop_loss <= 0:
            return self._reject(
                reason_code=RiskDecisionReason.INVALID_STOP_LOSS,
                reason="stop_loss must be greater than zero.",
            )

        if request.entry_price == request.stop_loss:
            return self._reject(
                reason_code=RiskDecisionReason.INVALID_STOP_LOSS,
                reason="entry_price and stop_loss cannot be equal.",
            )

        if request.direction() == RiskDirection.LONG and request.stop_loss >= request.entry_price:
            return self._reject(
                reason_code=RiskDecisionReason.INVALID_STOP_LOSS,
                reason="For a LONG trade, stop_loss must be below entry_price.",
            )
        if request.direction() == RiskDirection.SHORT and request.stop_loss <= request.entry_price:
            return self._reject(
                reason_code=RiskDecisionReason.INVALID_STOP_LOSS,
                reason="For a SHORT trade, stop_loss must be above entry_price.",
            )
        return None

    @staticmethod
    def _reject(*, reason_code: RiskDecisionReason, reason: str) -> RiskDecision:
        return RiskDecision(
            approved=False,
            reason_code=reason_code.value,
            reason=reason,
            warnings=[],
            evaluated_at=datetime.now(UTC),
        )


class TakeProfitRule(RiskRule):
    """Validate take-profit placement with direction-aware logic."""

    def evaluate(self, context: RiskContext) -> RiskDecision | None:
        request = context.request
        if request.take_profit is None:
            if context.config.take_profit_required:
                return self._reject(
                    reason_code=RiskDecisionReason.INVALID_TAKE_PROFIT,
                    reason="A valid take_profit is required for this trade.",
                )
            return None

        if request.take_profit <= 0:
            return self._reject(
                reason_code=RiskDecisionReason.INVALID_TAKE_PROFIT,
                reason="take_profit must be greater than zero.",
            )

        if request.direction() == RiskDirection.LONG and request.take_profit <= request.entry_price:
            return self._reject(
                reason_code=RiskDecisionReason.INVALID_TAKE_PROFIT,
                reason="For a LONG trade, take_profit must be above entry_price.",
            )
        if (
            request.direction() == RiskDirection.SHORT
            and request.take_profit >= request.entry_price
        ):
            return self._reject(
                reason_code=RiskDecisionReason.INVALID_TAKE_PROFIT,
                reason="For a SHORT trade, take_profit must be below entry_price.",
            )
        return None

    @staticmethod
    def _reject(*, reason_code: RiskDecisionReason, reason: str) -> RiskDecision:
        return RiskDecision(
            approved=False,
            reason_code=reason_code.value,
            reason=reason,
            warnings=[],
            evaluated_at=datetime.now(UTC),
        )


class RiskLimitRule(RiskRule):
    """Reject trades whose risk exceeds the configured maximum risk per trade."""

    def evaluate(self, context: RiskContext) -> RiskDecision | None:
        if context.config.max_risk_per_trade is None:
            return None
        if context.risk_amount > context.config.max_risk_per_trade:
            return RiskDecision(
                approved=False,
                reason_code=RiskDecisionReason.RISK_LIMIT_EXCEEDED.value,
                reason=(
                    "Calculated risk_amount exceeds the configured maximum risk limit of "
                    f"{context.config.max_risk_per_trade}."
                ),
                risk_amount=context.risk_amount,
                position_size=context.position_size,
                risk_reward_ratio=context.risk_reward_ratio,
                portfolio_exposure=context.proposed_exposure,
                warnings=context.warnings,
                evaluated_at=datetime.now(UTC),
            )
        return None


class PositionSizeRule(RiskRule):
    """Reject trades whose position size exceeds the configured maximum."""

    def evaluate(self, context: RiskContext) -> RiskDecision | None:
        if context.position_size > context.config.max_position_size:
            return RiskDecision(
                approved=False,
                reason_code=RiskDecisionReason.POSITION_SIZE_EXCEEDED.value,
                reason=(
                    "Calculated position_size exceeds the configured maximum limit "
                    f"of {context.config.max_position_size}."
                ),
                risk_amount=context.risk_amount,
                position_size=context.position_size,
                risk_reward_ratio=context.risk_reward_ratio,
                portfolio_exposure=context.proposed_exposure,
                warnings=context.warnings,
                evaluated_at=datetime.now(UTC),
            )
        return None


class RiskRewardRule(RiskRule):
    """Reject trades whose risk/reward ratio falls below the configured minimum."""

    def evaluate(self, context: RiskContext) -> RiskDecision | None:
        if context.risk_reward_ratio < context.config.min_risk_reward_ratio:
            return RiskDecision(
                approved=False,
                reason_code=RiskDecisionReason.INSUFFICIENT_RISK_REWARD.value,
                reason=(
                    "Risk/reward ratio is below the configured minimum of "
                    f"{context.config.min_risk_reward_ratio}."
                ),
                risk_amount=context.risk_amount,
                position_size=context.position_size,
                risk_reward_ratio=context.risk_reward_ratio,
                portfolio_exposure=context.proposed_exposure,
                warnings=context.warnings,
                evaluated_at=datetime.now(UTC),
            )
        return None


class PortfolioExposureRule(RiskRule):
    """Reject trades that would exceed maximum portfolio exposure."""

    def evaluate(self, context: RiskContext) -> RiskDecision | None:
        if context.portfolio_exposure.total_exposure > context.config.max_portfolio_exposure:
            return RiskDecision(
                approved=False,
                reason_code=RiskDecisionReason.PORTFOLIO_EXPOSURE_EXCEEDED.value,
                reason=(
                    "Proposed portfolio exposure exceeds the configured maximum of "
                    f"{context.config.max_portfolio_exposure}."
                ),
                risk_amount=context.risk_amount,
                position_size=context.position_size,
                risk_reward_ratio=context.risk_reward_ratio,
                portfolio_exposure=context.portfolio_exposure.total_exposure,
                warnings=context.warnings,
                evaluated_at=datetime.now(UTC),
            )
        return None


class DailyLossRule(RiskRule):
    """Reject trades when the configured daily loss limit has already been reached."""

    def evaluate(self, context: RiskContext) -> RiskDecision | None:
        if context.request.daily_loss is None:
            return None
        if context.request.daily_loss >= context.config.max_daily_loss:
            return RiskDecision(
                approved=False,
                reason_code=RiskDecisionReason.DAILY_LOSS_LIMIT_EXCEEDED.value,
                reason=(
                    "Daily loss exceeds the configured maximum of "
                    f"{context.config.max_daily_loss}."
                ),
                risk_amount=context.risk_amount,
                position_size=context.position_size,
                risk_reward_ratio=context.risk_reward_ratio,
                portfolio_exposure=context.proposed_exposure,
                warnings=context.warnings,
                evaluated_at=datetime.now(UTC),
            )
        return None


class DrawdownRule(RiskRule):
    """Reject trades when current drawdown exceeds the configured maximum."""

    def evaluate(self, context: RiskContext) -> RiskDecision | None:
        if context.drawdown_percent is None:
            return None
        if context.drawdown_percent >= context.config.max_drawdown_percent:
            return RiskDecision(
                approved=False,
                reason_code=RiskDecisionReason.DRAWDOWN_LIMIT_EXCEEDED.value,
                reason=(
                    "Drawdown exceeds the configured maximum of "
                    f"{context.config.max_drawdown_percent}."
                ),
                risk_amount=context.risk_amount,
                position_size=context.position_size,
                risk_reward_ratio=context.risk_reward_ratio,
                portfolio_exposure=context.proposed_exposure,
                warnings=context.warnings,
                evaluated_at=datetime.now(UTC),
            )
        return None


class OpenPositionRule(RiskRule):
    """Reject trades that would exceed maximum open positions."""

    def evaluate(self, context: RiskContext) -> RiskDecision | None:
        if context.request.open_positions is None:
            return None
        if context.request.open_positions >= context.config.max_open_positions:
            return RiskDecision(
                approved=False,
                reason_code=RiskDecisionReason.OPEN_POSITION_LIMIT_EXCEEDED.value,
                reason=(
                    "Open positions already meet or exceed the configured maximum of "
                    f"{context.config.max_open_positions}."
                ),
                risk_amount=context.risk_amount,
                position_size=context.position_size,
                risk_reward_ratio=context.risk_reward_ratio,
                portfolio_exposure=context.proposed_exposure,
                warnings=context.warnings,
                evaluated_at=datetime.now(UTC),
            )
        return None


class RiskManagementService:
    """Deterministic risk-evaluation engine with fail-closed behavior."""

    def __init__(
        self,
        config: RiskConfiguration | None = None,
        rules: list[RiskRule] | None = None,
    ) -> None:
        self.config = config or RiskConfiguration()
        self.config.validate()
        self.rules = rules or [
            InputValidationRule(),
            StopLossRule(),
            TakeProfitRule(),
            RiskLimitRule(),
            PositionSizeRule(),
            RiskRewardRule(),
            PortfolioExposureRule(),
            DailyLossRule(),
            DrawdownRule(),
            OpenPositionRule(),
        ]

    def evaluate(self, request: RiskRequest | dict[str, object]) -> RiskDecision:
        """Return a deterministic risk decision for a trade proposal."""
        try:
            normalized_request = self._normalize_request(request)
            context = self._build_context(normalized_request)
        except (TypeError, ValueError, InvalidOperation):
            return RiskDecision(
                approved=False,
                reason_code=RiskDecisionReason.INVALID_INPUT.value,
                reason="Risk request contains missing or invalid inputs.",
                warnings=[],
                evaluated_at=datetime.now(UTC),
            )

        for rule in self.rules:
            decision = rule.evaluate(context)
            if decision is not None:
                return decision

        return RiskDecision(
            approved=True,
            reason_code=RiskDecisionReason.APPROVED.value,
            reason="Risk checks passed.",
            risk_amount=context.risk_amount,
            position_size=context.position_size,
            risk_reward_ratio=context.risk_reward_ratio,
            portfolio_exposure=context.proposed_exposure,
            warnings=context.warnings,
            evaluated_at=datetime.now(UTC),
        )

    @staticmethod
    def _normalize_request(request: RiskRequest | dict[str, object]) -> RiskRequest:
        if isinstance(request, RiskRequest):
            return request
        return RiskRequest.from_mapping(request)

    def _build_context(self, request: RiskRequest) -> RiskContext:
        required_risk_amount = request.account_equity or Decimal("0")
        raw_risk_amount = required_risk_amount * self.config.risk_per_trade_percent
        if self.config.max_risk_per_trade is not None:
            raw_risk_amount = min(raw_risk_amount, self.config.max_risk_per_trade)

        if request.stop_loss is None:
            risk_distance = Decimal("0")
        else:
            risk_distance = abs(request.entry_price - request.stop_loss)

        if risk_distance <= 0:
            position_size = Decimal("0")
        else:
            position_size = raw_risk_amount / risk_distance

        if request.stop_loss is None or risk_distance <= 0:
            risk_reward_ratio = Decimal("0")
        else:
            if request.direction() == RiskDirection.LONG:
                reward_distance = abs(
                    (request.take_profit or request.entry_price) - request.entry_price
                )
            else:
                reward_distance = abs(
                    request.entry_price - (request.take_profit or request.entry_price)
                )
            if reward_distance <= 0:
                risk_reward_ratio = Decimal("0")
            else:
                risk_reward_ratio = reward_distance / risk_distance

        if request.current_exposure is None:
            proposed_exposure = Decimal("0")
        else:
            proposed_exposure = position_size * request.entry_price

        if request.current_exposure is None:
            portfolio_exposure = PortfolioExposure(
                current_exposure=Decimal("0"),
                proposed_exposure=proposed_exposure,
                total_exposure=proposed_exposure,
                max_portfolio_exposure=self.config.max_portfolio_exposure,
            )
        else:
            portfolio_exposure = PortfolioExposure(
                current_exposure=request.current_exposure,
                proposed_exposure=proposed_exposure,
                total_exposure=request.current_exposure + proposed_exposure,
                max_portfolio_exposure=self.config.max_portfolio_exposure,
            )

        if (
            request.peak_equity is not None
            and request.current_equity is not None
            and request.peak_equity > 0
        ):
            drawdown_percent = (
                request.peak_equity - request.current_equity
            ) / request.peak_equity
        else:
            drawdown_percent = None

        return RiskContext(
            request=request,
            config=self.config,
            risk_amount=raw_risk_amount,
            position_size=position_size,
            risk_reward_ratio=risk_reward_ratio,
            proposed_exposure=proposed_exposure,
            portfolio_exposure=portfolio_exposure,
            drawdown_percent=drawdown_percent,
            warnings=[],
        )


__all__ = [
    "DailyLossRule",
    "DrawdownRule",
    "InputValidationRule",
    "OpenPositionRule",
    "PortfolioExposureRule",
    "PositionSizeRule",
    "RiskLimitRule",
    "RiskManagementService",
    "RiskRewardRule",
    "RiskRule",
    "StopLossRule",
    "TakeProfitRule",
]
