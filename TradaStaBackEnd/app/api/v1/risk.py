"""Risk-management API endpoints."""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from typing import Annotated, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict

from app.application.risk_management.service import RiskManagementService
from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.domain.risk_management.models import RiskDecision, RiskRequest

router = APIRouter(tags=["risk-management"])


def format_decimal(value: Decimal) -> str:
    """Render a Decimal in a stable two-decimal string for API responses."""
    return str(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


class RiskEvaluationRequest(BaseModel):
    """API payload describing a proposed trade to be risk-evaluated."""

    symbol: str
    side: Literal["LONG", "SHORT"]
    entry_price: Decimal
    stop_loss: Decimal | None = None
    take_profit: Decimal | None = None
    account_equity: Decimal | None = None
    current_exposure: Decimal | None = None
    daily_loss: Decimal | None = None
    peak_equity: Decimal | None = None
    current_equity: Decimal | None = None
    open_positions: int | None = None


class RiskDecisionResponse(BaseModel):
    """Stable response model returned by the risk-evaluation API."""

    approved: bool
    reason_code: str
    reason: str
    risk_amount: str | None = None
    position_size: str | None = None
    risk_reward_ratio: str | None = None
    portfolio_exposure: str | None = None
    warnings: list[str] = []
    model_config = ConfigDict(use_enum_values=True)

    @staticmethod
    def from_decision(decision: RiskDecision) -> RiskDecisionResponse:
        return RiskDecisionResponse(
            approved=decision.approved,
            reason_code=decision.reason_code,
            reason=decision.reason,
            risk_amount=(
                format_decimal(decision.risk_amount)
                if decision.risk_amount is not None
                else None
            ),
            position_size=(
                format_decimal(decision.position_size)
                if decision.position_size is not None
                else None
            ),
            risk_reward_ratio=(
                format_decimal(decision.risk_reward_ratio)
                if decision.risk_reward_ratio is not None
                else None
            ),
            portfolio_exposure=(
                format_decimal(decision.portfolio_exposure)
                if decision.portfolio_exposure is not None
                else None
            ),
            warnings=decision.warnings,
        )


@router.post("/risk/evaluate")
async def evaluate_risk(
    payload: RiskEvaluationRequest,
    risk_service: Annotated[RiskManagementService, Depends(lambda: RiskManagementService())],
    current_user: Annotated[User | None, Depends(get_current_user)] = None,
) -> RiskDecisionResponse:
    """Accept a trade proposal and return a deterministic risk verdict."""
    request = RiskRequest.from_mapping(payload.model_dump())
    decision = risk_service.evaluate(request)
    return RiskDecisionResponse.from_decision(decision)


__all__ = ["RiskDecisionResponse", "RiskEvaluationRequest", "router"]
