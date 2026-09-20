"""Retrieval service for Moss-style semantic context grounding."""

from __future__ import annotations

import re
from collections.abc import Sequence

from app.domain.knowledge.models import RetrievalDocument, RetrievalMatch


class SemanticRetrievalService:
    """Rank local knowledge documents for a symbol and market context."""

    def __init__(self, corpus: Sequence[RetrievalDocument] | None = None) -> None:
        self.corpus = list(corpus or self._default_corpus())

    async def retrieve(
        self,
        symbol: str,
        *,
        timeframe: str = "1h",
        trend: str = "NEUTRAL",
        risk_profile: str = "balanced",
        intent: str = "evaluate_trade",
        query: str | None = None,
        limit: int = 5,
    ) -> list[RetrievalMatch]:
        """Return the most relevant documents for the requested market context."""
        normalized_symbol = symbol.strip().upper()
        normalized_query = self._build_query(
            normalized_symbol,
            timeframe=timeframe,
            trend=trend,
            risk_profile=risk_profile,
            intent=intent,
            query=query,
        )
        query_tokens = self._tokenize(normalized_query)

        ranked: list[tuple[RetrievalMatch, float]] = []
        for document in self.corpus:
            score = self._score_document(
                document,
                symbol=normalized_symbol,
                timeframe=timeframe,
                trend=trend,
                risk_profile=risk_profile,
                intent=intent,
                query_tokens=query_tokens,
            )
            if score <= 0:
                continue
            ranked.append(
                (
                    RetrievalMatch(
                        id=document.id,
                        title=document.title,
                        category=document.category,
                        summary=document.summary,
                        content=document.content,
                        score=round(score, 4),
                        source=document.source,
                        tags=document.tags,
                    ),
                    score,
                )
            )

        ranked.sort(key=lambda item: item[1], reverse=True)
        return [match for match, _ in ranked[: max(limit, 1)]]

    @staticmethod
    def _default_corpus() -> list[RetrievalDocument]:
        return [
            RetrievalDocument(
                id="trend-following-bullish",
                title="Trend-following playbook",
                category="strategy_playbook",
                summary="Bullish continuation is strongest when price stays above its trend baseline and momentum expands.",
                content="Use a trend-following setup when the asset remains above its moving-average baseline and momentum indicators stay constructive; avoid chasing late breakouts without confirmation from volume or clean support.",
                source="local_corpus",
                tags=("trend", "momentum", "bullish", "breakout"),
            ),
            RetrievalDocument(
                id="risk-on-macro",
                title="Risk-on regime",
                category="macro_context",
                summary="Risk-on environments support continued participation when conviction stays strong and volatility remains manageable.",
                content="A risk-on regime can support further upside in assets with strong relative strength; keep the portfolio aligned to the higher-conviction names and avoid excessive exposure when liquidity is thinning.",
                source="local_corpus",
                tags=("risk_on", "macro", "market_regime", "upside"),
            ),
            RetrievalDocument(
                id="volatility-risk-control",
                title="Volatility risk control",
                category="risk_policy",
                summary="Always widen stop-loss distances and reduce position sizing when volatility expands during sharp price moves.",
                content="When volatility spikes, favour smaller position sizes and wider risk bands to protect capital. Position sizing should scale with realized volatility and avoid over-concentrated exposure to a single asset.",
                source="local_corpus",
                tags=("risk", "volatility", "position_sizing", "stop_loss"),
            ),
            RetrievalDocument(
                id="mean-reversion-bearish",
                title="Mean-reversion watchlist",
                category="market_regime",
                summary="Bearish setups gain quality once price breaks support and momentum fails to recover above short-term resistance.",
                content="Short setups become more credible when price fails to reclaim support and trend indicators roll over. Favor risk-framed entries with a clean invalidation above the recent swing structure.",
                source="local_corpus",
                tags=("bearish", "mean_reversion", "support", "breakdown"),
            ),
            RetrievalDocument(
                id="execution-quality",
                title="Execution quality checklist",
                category="execution",
                summary="Prioritize clean entries, disciplined exits, and confirmation from multiple signals before acting on a trade idea.",
                content="Execution quality improves when the setup respects trend context, liquidity, and a clear invalidation level. Remove emotional bias and align the trade with the prevailing market regime.",
                source="local_corpus",
                tags=("execution", "discipline", "entry", "exit"),
            ),
        ]

    @staticmethod
    def _tokenize(value: str) -> set[str]:
        return {
            token for token in re.findall(r"[a-z0-9]+", value.lower()) if len(token) > 1
        }

    @staticmethod
    def _build_query(
        symbol: str,
        *,
        timeframe: str,
        trend: str,
        risk_profile: str,
        intent: str,
        query: str | None,
    ) -> str:
        base = f"{symbol} {timeframe} {trend.lower()} {risk_profile} {intent}"
        return f"{base} {query}" if query else base

    def _score_document(
        self,
        document: RetrievalDocument,
        *,
        symbol: str,
        timeframe: str,
        trend: str,
        risk_profile: str,
        intent: str,
        query_tokens: set[str],
    ) -> float:
        text = " ".join(
            [
                document.title,
                document.summary,
                document.content,
                " ".join(document.tags),
                document.category,
            ]
        ).lower()
        all_tokens = self._tokenize(text)
        overlap = len(query_tokens & all_tokens)
        symbol_hits = 1 if symbol.lower() in text else 0
        timeframe_hits = 1 if timeframe.lower() in text else 0
        trend_hits = 1 if trend.lower() in text else 0
        risk_hits = 1 if risk_profile.lower() in text else 0
        intent_hits = 1 if intent.lower() in text else 0

        category_boost = {
            "strategy_playbook": 1.2,
            "macro_context": 1.0,
            "risk_policy": 1.5,
            "market_regime": 1.1,
            "execution": 0.8,
        }.get(document.category, 0.5)

        weighted_score = (
            overlap * 1.8
            + symbol_hits * 2.0
            + timeframe_hits * 0.8
            + trend_hits * 1.5
            + risk_hits * 1.4
            + intent_hits * 0.9
            + category_boost
        )
        return weighted_score


__all__ = ["SemanticRetrievalService"]
