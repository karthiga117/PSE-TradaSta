"""Semantic retrieval API endpoints."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field

from app.application.knowledge.retrieval_service import SemanticRetrievalService
from app.core.dependencies import context_retrieval_service_dependency

router = APIRouter(tags=["context-retrieval"])


class ContextRetrievalRequest(BaseModel):
    """Request payload for semantic context retrieval."""

    symbol: str
    timeframe: str = "1h"
    trend: Literal["BULLISH", "BEARISH", "NEUTRAL"] = "NEUTRAL"
    risk_profile: str = "balanced"
    intent: str = "evaluate_trade"
    query: str | None = None
    limit: int = Field(default=5, ge=1, le=10)


class RetrievalDocumentResponse(BaseModel):
    """A single ranked document returned from the retrieval layer."""

    id: str
    title: str
    category: str
    summary: str
    score: float
    source: str
    tags: list[str] = Field(default_factory=list)


class ContextRetrievalResponse(BaseModel):
    """Response payload for the semantic retrieval endpoint."""

    symbol: str
    timeframe: str
    trend: str
    risk_profile: str
    intent: str
    query: str
    generated_at: datetime
    documents: list[RetrievalDocumentResponse]

    model_config = ConfigDict(use_enum_values=True)


@router.post("/context/retrieve")
async def retrieve_context(
    payload: ContextRetrievalRequest,
    retrieval_service: Annotated[
        SemanticRetrievalService, Depends(context_retrieval_service_dependency)
    ],
) -> ContextRetrievalResponse:
    """Return ranked local knowledge documents that are relevant to the selected market context."""
    matches = await retrieval_service.retrieve(
        payload.symbol,
        timeframe=payload.timeframe,
        trend=payload.trend,
        risk_profile=payload.risk_profile,
        intent=payload.intent,
        query=payload.query,
        limit=payload.limit,
    )
    return ContextRetrievalResponse(
        symbol=payload.symbol.upper(),
        timeframe=payload.timeframe,
        trend=payload.trend,
        risk_profile=payload.risk_profile,
        intent=payload.intent,
        query=payload.query or "",
        generated_at=datetime.now(UTC),
        documents=[
            RetrievalDocumentResponse(
                id=item.id,
                title=item.title,
                category=item.category,
                summary=item.summary,
                score=item.score,
                source=item.source,
                tags=list(item.tags),
            )
            for item in matches
        ],
    )


__all__ = ["ContextRetrievalRequest", "ContextRetrievalResponse", "router"]
