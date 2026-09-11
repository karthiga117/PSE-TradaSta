"""Application exception types and FastAPI handlers."""

import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class ApplicationException(Exception):
    """Base exception for expected application-level failures."""

    def __init__(
        self, message: str, code: str = "APPLICATION_ERROR", status_code: int = 400
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code


class MarketDataError(ApplicationException):
    """Raised when the upstream market-data provider fails or returns invalid data."""

    def __init__(self, message: str, status_code: int = 502) -> None:
        super().__init__(message, code="MARKET_DATA_ERROR", status_code=status_code)


class TechnicalAnalysisError(ApplicationException):
    """Raised when technical-analysis input data or calculations are invalid."""

    def __init__(
        self,
        message: str,
        code: str = "TECHNICAL_ANALYSIS_ERROR",
        status_code: int = 422,
    ) -> None:
        super().__init__(message, code=code, status_code=status_code)


class InsufficientMarketDataError(TechnicalAnalysisError):
    """Raised when there are not enough normalized candles to calculate an indicator."""

    def __init__(self, message: str) -> None:
        super().__init__(message, code="INSUFFICIENT_MARKET_DATA", status_code=422)


class InvalidCandleError(TechnicalAnalysisError):
    """Raised when one or more OHLCV candles violate consistency checks."""

    def __init__(self, message: str) -> None:
        super().__init__(message, code="INVALID_CANDLE_DATA", status_code=422)


class InvalidIndicatorConfigurationError(TechnicalAnalysisError):
    """Raised when indicator configuration violates the technical-analysis contract."""

    def __init__(self, message: str) -> None:
        super().__init__(message, code="INVALID_INDICATOR_CONFIGURATION", status_code=422)


async def application_exception_handler(
    request: Request, exception: Exception
) -> JSONResponse:
    """Return a stable error envelope for expected application failures."""
    if not isinstance(exception, ApplicationException):
        return await unexpected_exception_handler(request, exception)

    return JSONResponse(
        status_code=exception.status_code,
        content={"error": {"code": exception.code, "message": exception.message}},
    )


async def unexpected_exception_handler(_: Request, exception: Exception) -> JSONResponse:
    """Hide implementation details while recording unexpected failures server-side."""
    logger.exception("Unhandled application error: %s", exception)
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred.",
            }
        },
    )


def register_exception_handlers(application: FastAPI) -> None:
    """Register application-wide exception handlers."""
    application.add_exception_handler(ApplicationException, application_exception_handler)
    application.add_exception_handler(Exception, unexpected_exception_handler)
