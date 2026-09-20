"""Central router for version 1 APIs."""

from fastapi import APIRouter

from app.api.v1.analysis import router as analysis_router
from app.api.v1.knowledge import router as knowledge_router
from app.api.v1.context import router as context_router
from app.api.v1.market_data import router as market_data_router
from app.api.v1.risk import router as risk_router
from app.api.v1.telegram import router as telegram_router
from app.auth.router import router as auth_router
from app.api.v1.signals import router as signals_router
from app.health.router import router as health_router

router = APIRouter()
router.include_router(health_router)
router.include_router(auth_router)
router.include_router(market_data_router)
router.include_router(analysis_router)
router.include_router(context_router)
router.include_router(risk_router)
router.include_router(signals_router)
router.include_router(knowledge_router)
router.include_router(telegram_router)
