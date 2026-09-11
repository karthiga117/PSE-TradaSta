"""Tests for the deterministic risk-management engine."""

from dataclasses import replace
from decimal import Decimal

from fastapi.testclient import TestClient

from app.application.risk_management.service import RiskManagementService
from app.domain.risk_management.models import RiskConfiguration, RiskDirection, RiskRequest
from app.main import app

client = TestClient(app)


def build_request(**overrides: object) -> RiskRequest:
    request = RiskRequest(
        symbol="BTCUSDT",
        side=RiskDirection.LONG,
        entry_price=Decimal("100"),
        stop_loss=Decimal("95"),
        take_profit=Decimal("110"),
        account_equity=Decimal("10000"),
        current_exposure=Decimal("2000"),
        daily_loss=Decimal("50"),
        peak_equity=Decimal("10000"),
        current_equity=Decimal("9900"),
        open_positions=2,
    )
    return replace(request, **overrides)


def test_risk_service_approves_valid_long_trade() -> None:
    service = RiskManagementService(
        config=RiskConfiguration(
            risk_per_trade_percent=Decimal("0.01"),
            max_position_size=Decimal("1000"),
            max_portfolio_exposure=Decimal("50000"),
            max_daily_loss=Decimal("500"),
            max_drawdown_percent=Decimal("0.10"),
            min_risk_reward_ratio=Decimal("2.0"),
            max_open_positions=5,
        )
    )

    decision = service.evaluate(build_request())

    assert decision.approved is True
    assert decision.reason_code == "APPROVED"
    assert decision.risk_amount == Decimal("100")
    assert decision.position_size == Decimal("20")
    assert decision.risk_reward_ratio == Decimal("2")


def test_risk_service_rejects_invalid_short_stop_loss() -> None:
    service = RiskManagementService()

    decision = service.evaluate(
        build_request(
            side=RiskDirection.SHORT,
            entry_price=Decimal("100"),
            stop_loss=Decimal("95"),
            take_profit=Decimal("90"),
        )
    )

    assert decision.approved is False
    assert decision.reason_code == "INVALID_STOP_LOSS"


def test_risk_service_rejects_low_risk_reward() -> None:
    service = RiskManagementService(
        config=RiskConfiguration(
            risk_per_trade_percent=Decimal("0.01"),
            max_position_size=Decimal("1000"),
            max_portfolio_exposure=Decimal("50000"),
            max_daily_loss=Decimal("500"),
            max_drawdown_percent=Decimal("0.10"),
            min_risk_reward_ratio=Decimal("2.0"),
            max_open_positions=5,
        )
    )

    decision = service.evaluate(
        build_request(
            stop_loss=Decimal("90"),
            take_profit=Decimal("105"),
        )
    )

    assert decision.approved is False
    assert decision.reason_code == "INSUFFICIENT_RISK_REWARD"


def test_risk_service_rejects_drawdown_limit() -> None:
    service = RiskManagementService(
        config=RiskConfiguration(
            risk_per_trade_percent=Decimal("0.01"),
            max_position_size=Decimal("1000"),
            max_portfolio_exposure=Decimal("50000"),
            max_daily_loss=Decimal("500"),
            max_drawdown_percent=Decimal("0.10"),
            min_risk_reward_ratio=Decimal("2.0"),
            max_open_positions=5,
        )
    )

    decision = service.evaluate(
        build_request(
            peak_equity=Decimal("10000"),
            current_equity=Decimal("8500"),
        )
    )

    assert decision.approved is False
    assert decision.reason_code == "DRAWDOWN_LIMIT_EXCEEDED"


def test_api_risk_evaluation_returns_structured_decision() -> None:
    payload = {
        "symbol": "BTCUSDT",
        "side": "LONG",
        "entry_price": "100",
        "stop_loss": "95",
        "take_profit": "110",
        "account_equity": "10000",
        "current_exposure": "2000",
        "daily_loss": "50",
        "peak_equity": "10000",
        "current_equity": "9900",
        "open_positions": 2,
    }

    response = client.post("/api/v1/risk/evaluate", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["approved"] is True
    assert body["reason_code"] == "APPROVED"
    assert body["risk_amount"] == "100.00"
    assert body["position_size"] == "20.00"
