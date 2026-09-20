"""Reusable trading-analysis orchestration used by the Telegram assistant."""

from __future__ import annotations

import re
from decimal import Decimal
from types import SimpleNamespace
from typing import Any

from app.application.knowledge.retrieval_service import SemanticRetrievalService
from app.application.market_data_service import MarketDataService
from app.application.risk_management.service import RiskManagementService
from app.application.technical_analysis.service import TechnicalAnalysisService
from app.core.exceptions import InsufficientMarketDataError
from app.domain.risk_management.models import RiskDirection, RiskRequest
from app.domain.technical_analysis.models import IndicatorConfig

_SYMBOL_ALIASES = {
    "BTC": "BTCUSDT",
    "ETH": "ETHUSDT",
    "SOL": "SOLUSDT",
    "ADA": "ADAUSDT",
    "XRP": "XRPUSDT",
    "DOGE": "DOGEUSDT",
}


def normalize_symbol(symbol: str) -> str:
    """Normalize common crypto symbol inputs into the backend's canonical pair form."""
    raw = (symbol or "").strip()
    if not raw:
        raise ValueError("symbol is required")

    candidate = raw.upper()
    if candidate.endswith("USDT"):
        return candidate
    if candidate.endswith("USD"):
        return f"{candidate[:-3]}USDT"
    if candidate in _SYMBOL_ALIASES:
        return _SYMBOL_ALIASES[candidate]
    if re.fullmatch(r"[A-Z0-9]{2,12}", candidate):
        return f"{candidate}USDT"
    raise ValueError(f"Unsupported symbol: {symbol}")


def format_decimal(value: Decimal | None) -> str:
    """Render Decimal values in a stable user-facing format."""
    if value is None:
        return "N/A"
    return format(value.normalize(), "f") if value == value.to_integral() else format(value, "f")


class TradingAnalysisService:
    """Compose market, technical, risk, and retrieval decisions into a single result."""

    def __init__(
        self,
        *,
        market_data_service: MarketDataService,
        retrieval_service: SemanticRetrievalService | None = None,
        risk_service: RiskManagementService | None = None,
    ) -> None:
        self.market_data_service = market_data_service
        self.retrieval_service = retrieval_service or SemanticRetrievalService()
        self.risk_service = risk_service or RiskManagementService()

    async def analyze(
        self,
        symbol: str,
        *,
        timeframe: str = "1h",
        risk_profile: str = "balanced",
        intent: str = "evaluate_trade",
    ) -> dict[str, Any]:
        """Run the deterministic market-analysis pipeline used by Telegram and dashboard flows."""
        normalized_symbol = normalize_symbol(symbol)
        price = await self.market_data_service.get_current_price(normalized_symbol)
        candles = await self.market_data_service.get_ohlcv(
            normalized_symbol,
            timeframe=timeframe,
            limit=48,
        )
        try:
            analysis = TechnicalAnalysisService(config=IndicatorConfig()).analyze(
                candles,
                symbol=normalized_symbol,
                timeframe=timeframe,
            )
        except InsufficientMarketDataError:
            analysis = SimpleNamespace(
                trend=SimpleNamespace(value="NEUTRAL"),
                rsi=SimpleNamespace(value=Decimal("50")),
            )

        signal = self._derive_signal(analysis.trend.value)
        decision = self._evaluate_risk(normalized_symbol, price.price, signal)
        documents = await self.retrieval_service.retrieve(
            normalized_symbol,
            timeframe=timeframe,
            trend=analysis.trend.value,
            risk_profile=risk_profile,
            intent=intent,
            limit=5,
        )
        explanation = self._build_explanation(
            normalized_symbol,
            signal=signal,
            trend=analysis.trend.value,
            decision=decision,
            documents=documents,
            price=price.price,
        )

        confidence = self._estimate_confidence(analysis.rsi.value if analysis.rsi else Decimal("50"))
        return {
            "symbol": normalized_symbol,
            "timeframe": timeframe,
            "trend": analysis.trend.value,
            "signal": signal,
            "confidence": confidence,
            "price": price.price,
            "risk_decision": decision,
            "explanation": explanation,
            "documents": documents,
        }

    @staticmethod
    def _derive_signal(trend: str) -> str:
        """Translate the deterministic trend into a stable signal."""
        trend_key = (trend or "NEUTRAL").upper()
        if trend_key == "BULLISH":
            return "BUY"
        if trend_key == "BEARISH":
            return "SELL"
        return "HOLD"

    def _evaluate_risk(self, symbol: str, entry_price: Decimal, signal: str) -> Any:
        """Evaluate the trade using the shared risk engine to maintain the single source of truth."""
        if signal == "BUY":
            side = RiskDirection.LONG
            stop_loss = entry_price * Decimal("0.98")
            take_profit = entry_price * Decimal("1.07")
        elif signal == "SELL":
            side = RiskDirection.SHORT
            stop_loss = entry_price * Decimal("1.02")
            take_profit = entry_price * Decimal("0.93")
        else:
            side = RiskDirection.LONG
            stop_loss = entry_price * Decimal("0.99")
            take_profit = entry_price * Decimal("1.01")

        request = RiskRequest(
            symbol=symbol,
            side=side,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            account_equity=Decimal("10000"),
            current_exposure=Decimal("0"),
            daily_loss=Decimal("0"),
            peak_equity=Decimal("10000"),
            current_equity=Decimal("10000"),
            open_positions=0,
        )
        return self.risk_service.evaluate(request)

    @staticmethod
    def _estimate_confidence(rsi_value: Decimal) -> int:
        """Map RSI into a bounded confidence value for Telegram summaries."""
        normalized = min(max(float(rsi_value), 10.0), 90.0)
        confidence = int(round(normalized))
        return max(55, min(94, confidence))

    @staticmethod
    def _build_explanation(
        symbol: str,
        *,
        signal: str,
        trend: str,
        decision: Any,
        documents: list[Any],
        price: Decimal,
    ) -> str:
        """Produce a deterministic explanation grounded in the existing retrieval corpus."""
        doc_summary = documents[0].summary if documents else "No additional context was retrieved."
        risk_status = "APPROVED" if getattr(decision, "approved", False) else "REJECTED"
        return (
            f"{symbol} is currently {trend.lower()} with a system signal of {signal}. "
            f"Price is {format_decimal(price)} and the risk engine returned {risk_status}. "
            f"Context: {doc_summary} The model is explaining the system-generated decision, "
            "not overriding it."
        )


def parse_telegram_command(text: str) -> dict[str, Any]:
    """Parse common Telegram commands and natural-language queries into a normalized intent."""
    cleaned = (text or "").strip()
    if not cleaned:
        return {"intent": "help", "symbol": None, "timeframe": "1h"}

    lower = cleaned.lower()
    if lower.startswith("/start"):
        return {"intent": "start", "symbol": None, "timeframe": "1h"}
    if lower.startswith("/help"):
        return {"intent": "help", "symbol": None, "timeframe": "1h"}
    if lower.startswith("/price"):
        return {
            "intent": "price",
            "symbol": extract_symbol(cleaned[6:]),
            "timeframe": "1h",
        }
    if lower.startswith("/analyze"):
        return {
            "intent": "analyze",
            "symbol": extract_symbol(cleaned[8:]),
            "timeframe": "1h",
        }
    if lower.startswith("/signal"):
        return {
            "intent": "signal",
            "symbol": extract_symbol(cleaned[7:]),
            "timeframe": "1h",
        }
    if lower.startswith("/risk"):
        return {
            "intent": "risk",
            "symbol": extract_symbol(cleaned[5:]),
            "timeframe": "1h",
        }
    if lower.startswith("/explain"):
        return {
            "intent": "explain",
            "symbol": extract_symbol(cleaned[8:]),
            "timeframe": "1h",
        }

    if "ignore" in lower and "signal" in lower:
        return {"intent": "guardrail", "symbol": extract_symbol(cleaned), "timeframe": "1h"}
    if "price" in lower and ("btc" in lower or "eth" in lower or "sol" in lower):
        return {"intent": "price", "symbol": extract_symbol(cleaned), "timeframe": "1h"}
    if "signal" in lower:
        return {"intent": "signal", "symbol": extract_symbol(cleaned), "timeframe": "1h"}
    if "risk" in lower:
        return {"intent": "risk", "symbol": extract_symbol(cleaned), "timeframe": "1h"}
    if "explain" in lower or "why" in lower:
        return {"intent": "explain", "symbol": extract_symbol(cleaned), "timeframe": "1h"}
    if "analy" in lower:
        return {"intent": "analyze", "symbol": extract_symbol(cleaned), "timeframe": "1h"}

    return {"intent": "help", "symbol": None, "timeframe": "1h"}


def extract_symbol(text: str) -> str | None:
    """Extract the most likely market symbol from a Telegram message."""
    material = (text or "").strip()
    if not material:
        return None

    tokens = re.findall(r"[A-Za-z0-9]+", material)
    for token in tokens:
        candidate = token.upper()
        if candidate in _SYMBOL_ALIASES:
            return _SYMBOL_ALIASES[candidate]
        if candidate.endswith("USDT"):
            return candidate

    lower_text = material.lower()
    for alias, symbol in _SYMBOL_ALIASES.items():
        if alias.lower() in lower_text:
            return symbol
    if "btc" in lower_text:
        return "BTCUSDT"
    if "eth" in lower_text:
        return "ETHUSDT"
    if "sol" in lower_text:
        return "SOLUSDT"
    return None


def build_telegram_help_text() -> str:
    """Return the user-facing help menu for instruction-driven Telegram flows."""
    return (
        "Welcome to TradaSta.\n"
        "Available commands:\n"
        "/start\n"
        "/help\n"
        "/price BTCUSDT\n"
        "/analyze BTCUSDT\n"
        "/signal BTCUSDT\n"
        "/risk BTCUSDT\n"
        "/explain BTCUSDT\n\n"
        "Examples: Analyze BTCUSDT, Show BTCUSDT price, Why is the signal SELL?"
    )


__all__ = [
    "TradingAnalysisService",
    "build_telegram_help_text",
    "extract_symbol",
    "format_decimal",
    "normalize_symbol",
    "parse_telegram_command",
]
