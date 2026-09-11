"""Deterministic trading signal engine orchestration."""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any

from app.application.market_data_service import MarketDataService
from app.application.risk_management.service import RiskManagementService
from app.application.technical_analysis.service import TechnicalAnalysisService
from app.application.technical_analysis.strategies import StrategyRegistry, TechnicalStrategy
from app.core.config import Settings, get_settings
from app.domain.risk_management.models import RiskRequest
from app.domain.signal import ProposedTrade, SignalRequest, SignalValue, TradeSide, TradingSignal
from app.domain.technical_analysis.models import (
    StrategyObservation,
    TechnicalAnalysisResult,
    TrendDirection,
)

logger = logging.getLogger(__name__)


class SignalEngine:
    """Compose market-data, analysis, strategy, and risk decisions into a final signal."""

    def __init__(
        self,
        *,
        market_data_service: MarketDataService,
        technical_analysis_service: TechnicalAnalysisService,
        strategy_registry: StrategyRegistry,
        risk_service: RiskManagementService,
        settings: Settings | None = None,
    ) -> None:
        self.market_data_service = market_data_service
        self.technical_analysis_service = technical_analysis_service
        self.strategy_registry = strategy_registry
        self.risk_service = risk_service
        self.settings = settings or get_settings()

    async def generate_signal(self, request: SignalRequest | dict[str, Any]) -> TradingSignal:
        """Return a deterministic signal after validating all upstream dependencies."""
        normalized = (
            request
            if isinstance(request, SignalRequest)
            else SignalRequest.from_mapping(request)
        )
        symbol = normalized.symbol.strip()
        if not symbol:
            return self._hold(
                symbol=symbol,
                strategy_name=normalized.normalized_strategy_name(default=self.settings.default_strategy),
                reason="Invalid request: symbol is required.",
                price=None,
            )

        strategy_name = normalized.normalized_strategy_name(default=self.settings.default_strategy)
        current_price = None
        try:
            current_price = await self.market_data_service.get_current_price(symbol)
        except Exception as exc:  # pragma: no cover - defensive boundary
            logger.warning("Market data failure while generating signal for %s: %s", symbol, exc)
            return self._hold(
                symbol=symbol,
                strategy_name=strategy_name,
                reason=f"Insufficient market data for reliable signal generation: {exc}",
                price=None,
            )

        try:
            candles = await self.market_data_service.get_ohlcv(
                symbol,
                timeframe=normalized.timeframe,
                limit=200,
            )
            analysis = self.technical_analysis_service.analyze(
                candles,
                symbol=symbol,
                timeframe=normalized.timeframe,
            )
        except Exception as exc:  # pragma: no cover - defensive boundary
            logger.warning(
                "Technical analysis failure while generating signal for %s: %s",
                symbol,
                exc,
            )
            return self._hold(
                symbol=symbol,
                strategy_name=strategy_name,
                reason=f"Technical analysis unavailable: {exc}",
                price=current_price.price,
            )

        strategy = self._resolve_strategy(strategy_name)
        if strategy is None:
            return self._hold(
                symbol=symbol,
                strategy_name=strategy_name,
                reason=f"Strategy '{strategy_name}' was not found in the configured registry.",
                price=current_price.price,
                indicators=self._indicator_snapshot(analysis),
            )

        try:
            observation = strategy.evaluate(analysis)
        except ValueError as exc:
            logger.warning(
                "Strategy evaluation failure for %s using %s: %s",
                symbol,
                strategy_name,
                exc,
            )
            return self._hold(
                symbol=symbol,
                strategy_name=strategy_name,
                reason=f"Strategy evaluation failed: {exc}",
                price=current_price.price,
                indicators=self._indicator_snapshot(analysis),
            )

        candidate_signal = self._candidate_signal_from_direction(observation.direction)
        if candidate_signal == SignalValue.HOLD:
            return self._hold(
                symbol=symbol,
                strategy_name=observation.strategy_name,
                reason=f"Strategy produced a neutral trend: {observation.rationale}",
                price=current_price.price,
                indicators=self._indicator_snapshot(analysis),
                confidence=Decimal("0.00"),
            )

        confidence = self._calculate_confidence(analysis, observation, candidate_signal)
        if confidence < Decimal(str(self.settings.min_signal_confidence)):
            return self._hold(
                symbol=symbol,
                strategy_name=observation.strategy_name,
                reason=(
                    "Signal confidence is below the configured threshold. "
                    "Observed confidence "
                    f"{confidence} is below min {self.settings.min_signal_confidence}."
                ),
                price=current_price.price,
                indicators=self._indicator_snapshot(analysis),
                confidence=confidence,
            )

        trade = self._build_proposed_trade(
            symbol=symbol,
            signal=candidate_signal,
            price=current_price.price,
            analysis=analysis,
            strategy_name=observation.strategy_name,
            rationale=observation.rationale,
        )
        if trade.stop_loss is None or trade.take_profit is None:
            return self._hold(
                symbol=symbol,
                strategy_name=observation.strategy_name,
                reason="Missing required price or risk levels for a valid trade proposal.",
                price=current_price.price,
                indicators=self._indicator_snapshot(analysis),
                confidence=confidence,
            )

        side = (
            TradeSide.LONG.value
            if candidate_signal == SignalValue.BUY
            else TradeSide.SHORT.value
        )
        risk_request = RiskRequest.from_mapping(
            {
                "symbol": symbol,
                "side": side,
                "entry_price": trade.entry_price,
                "stop_loss": trade.stop_loss,
                "take_profit": trade.take_profit,
                "account_equity": normalized.account_equity,
                "current_exposure": normalized.current_exposure,
                "daily_loss": normalized.daily_loss,
                "peak_equity": normalized.peak_equity,
                "current_equity": normalized.current_equity,
                "open_positions": normalized.open_positions,
            }
        )

        try:
            decision = self.risk_service.evaluate(risk_request)
        except Exception as exc:  # pragma: no cover - defensive boundary
            logger.warning("Risk engine failure for %s: %s", symbol, exc)
            return self._hold(
                symbol=symbol,
                strategy_name=observation.strategy_name,
                reason=f"Risk evaluation unavailable: {exc}",
                price=current_price.price,
                indicators=self._indicator_snapshot(analysis),
                confidence=confidence,
            )

        if not decision.approved:
            return self._hold(
                symbol=symbol,
                strategy_name=observation.strategy_name,
                reason=(
                    "Risk evaluation rejected the proposed trade because "
                    f"{decision.reason.lower()}."
                ),
                price=current_price.price,
                indicators=self._indicator_snapshot(analysis),
                confidence=confidence,
                entry=trade.entry_price,
                stop_loss=trade.stop_loss,
                take_profit=trade.take_profit,
                risk_reward_ratio=trade.risk_reward_ratio,
            )

        return TradingSignal(
            signal=candidate_signal,
            symbol=symbol,
            price=current_price.price,
            indicators=self._indicator_snapshot(analysis),
            strategy=observation.strategy_name,
            confidence=confidence,
            entry=trade.entry_price,
            stop_loss=trade.stop_loss,
            take_profit=trade.take_profit,
            risk_reward_ratio=trade.risk_reward_ratio,
            reasoning=(
                f"{observation.rationale}. "
                f"Risk checks passed with a {trade.risk_reward_ratio} risk/reward ratio."
            ),
        )

    def _resolve_strategy(self, strategy_name: str) -> TechnicalStrategy | None:
        """Resolve the selected strategy from the registry."""
        try:
            return self.strategy_registry.get(strategy_name)
        except KeyError:
            return None

    @staticmethod
    def _candidate_signal_from_direction(direction: TrendDirection) -> SignalValue:
        """Map trend direction into a candidate trading signal."""
        if direction == TrendDirection.BULLISH:
            return SignalValue.BUY
        if direction == TrendDirection.BEARISH:
            return SignalValue.SELL
        return SignalValue.HOLD

    def _calculate_confidence(
        self,
        analysis: TechnicalAnalysisResult,
        observation: StrategyObservation,
        candidate: SignalValue,
    ) -> Decimal:
        """Return a deterministic 0.0 to 1.0 confidence score based on agreement."""
        checks: list[int] = []
        expected = (
            TrendDirection.BULLISH
            if candidate == SignalValue.BUY
            else TrendDirection.BEARISH
        )

        if analysis.trend == expected:
            checks.append(1)
        elif analysis.trend == TrendDirection.NEUTRAL:
            checks.append(0)
        else:
            checks.append(-1)

        if observation.direction == expected:
            checks.append(1)
        elif observation.direction == TrendDirection.NEUTRAL:
            checks.append(0)
        else:
            checks.append(-1)

        if analysis.rsi is not None:
            if candidate == SignalValue.BUY and analysis.rsi.value > Decimal("55"):
                checks.append(1)
            elif candidate == SignalValue.SELL and analysis.rsi.value < Decimal("45"):
                checks.append(1)
            elif analysis.rsi.value == Decimal("50"):
                checks.append(0)
            else:
                checks.append(-1)

        if analysis.macd is not None:
            if candidate == SignalValue.BUY and analysis.macd.macd > analysis.macd.signal:
                checks.append(1)
            elif candidate == SignalValue.SELL and analysis.macd.macd < analysis.macd.signal:
                checks.append(1)
            elif analysis.macd.macd == analysis.macd.signal:
                checks.append(0)
            else:
                checks.append(-1)

        if analysis.ema is not None and analysis.sma is not None:
            if candidate == SignalValue.BUY and analysis.ema.value > analysis.sma.value:
                checks.append(1)
            elif candidate == SignalValue.SELL and analysis.ema.value < analysis.sma.value:
                checks.append(1)
            elif analysis.ema.value == analysis.sma.value:
                checks.append(0)
            else:
                checks.append(-1)

        if not checks:
            return Decimal("0.00")

        score = sum(checks)
        total = Decimal(len(checks))
        normalized = (Decimal(score) + total) / (Decimal(2) * total)
        return max(Decimal("0.00"), min(Decimal("1.00"), normalized))

    def _build_proposed_trade(
        self,
        *,
        symbol: str,
        signal: SignalValue,
        price: Decimal,
        analysis: TechnicalAnalysisResult,
        strategy_name: str,
        rationale: str,
    ) -> ProposedTrade:
        """Construct a deterministic proposed trade from the candidate signal."""
        atr_value = Decimal("0") if analysis.atr is None else analysis.atr.value
        multiplier = Decimal(str(self.settings.atr_stop_multiplier))

        if signal == SignalValue.BUY:
            entry = price
            stop_loss = entry - (atr_value * multiplier)
            risk = entry - stop_loss
            take_profit = entry + (risk * Decimal(str(self.settings.target_risk_reward)))
            side = TradeSide.LONG
        elif signal == SignalValue.SELL:
            entry = price
            stop_loss = entry + (atr_value * multiplier)
            risk = stop_loss - entry
            take_profit = entry - (risk * Decimal(str(self.settings.target_risk_reward)))
            side = TradeSide.SHORT
        else:
            raise ValueError("Only BUY and SELL signals can produce a trade proposal")

        if atr_value <= 0:
            raise ValueError("ATR value must be positive for a valid stop-loss calculation")

        risk_reward_ratio = self._risk_reward_ratio(entry, stop_loss, take_profit, side)
        return ProposedTrade(
            symbol=symbol,
            side=side,
            entry_price=entry,
            stop_loss=stop_loss,
            take_profit=take_profit,
            strategy=strategy_name,
            rationale=rationale,
            risk_reward_ratio=risk_reward_ratio,
        )

    @staticmethod
    def _risk_reward_ratio(
        entry: Decimal,
        stop_loss: Decimal,
        take_profit: Decimal,
        side: TradeSide,
    ) -> Decimal:
        """Compute the reward/risk ratio for a trade proposal."""
        if side == TradeSide.LONG:
            risk = entry - stop_loss
            reward = take_profit - entry
        else:
            risk = stop_loss - entry
            reward = entry - take_profit
        if risk <= 0:
            raise ValueError("Risk distance must be positive for a valid trade proposal")
        return reward / risk

    @staticmethod
    def _indicator_snapshot(analysis: TechnicalAnalysisResult) -> dict[str, str]:
        """Return a compact indicator snapshot for signal payloads."""
        snapshot: dict[str, str] = {
            "trend": analysis.trend.value,
        }
        if analysis.rsi is not None:
            snapshot["rsi"] = str(analysis.rsi.value)
        if analysis.sma is not None:
            snapshot["sma"] = str(analysis.sma.value)
        if analysis.ema is not None:
            snapshot["ema"] = str(analysis.ema.value)
        if analysis.macd is not None:
            snapshot["macd"] = str(analysis.macd.macd)
            snapshot["macd_signal"] = str(analysis.macd.signal)
            snapshot["macd_histogram"] = str(analysis.macd.histogram)
        if analysis.atr is not None:
            snapshot["atr"] = str(analysis.atr.value)
        return snapshot

    def _hold(
        self,
        *,
        symbol: str,
        strategy_name: str,
        reason: str,
        price: Decimal | None,
        indicators: dict[str, str] | None = None,
        confidence: Decimal | None = None,
        entry: Decimal | None = None,
        stop_loss: Decimal | None = None,
        take_profit: Decimal | None = None,
        risk_reward_ratio: Decimal | None = None,
    ) -> TradingSignal:
        """Create a fail-closed HOLD signal with a meaningful explanation."""
        final_confidence = confidence if confidence is not None else Decimal("0.00")
        return TradingSignal(
            signal=SignalValue.HOLD,
            symbol=symbol,
            price=price,
            indicators=indicators or {},
            strategy=strategy_name,
            confidence=final_confidence,
            entry=entry,
            stop_loss=stop_loss,
            take_profit=take_profit,
            risk_reward_ratio=risk_reward_ratio,
            reasoning=reason,
        )


__all__ = ["SignalEngine"]
