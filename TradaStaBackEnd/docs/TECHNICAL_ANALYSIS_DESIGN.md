# Technical Analysis Design

## Purpose

The technical-analysis layer is intentionally provider-independent. It accepts normalized candle data from the market-data service, validates it, calculates deterministic indicators, and returns a stable analysis payload without depending on any specific provider or exchange API.

## Architecture

The flow is:

1. API route receives a symbol and query parameters.
2. The market-data service fetches OHLCV candles.
3. The technical-analysis service validates and normalizes the candle list.
4. Indicator functions compute deterministic values from the normalized OHLCV data.
5. Strategy observations summarize the current market regime without executing trades.
6. The API layer serializes the result into a versioned response model.

This keeps the domain model clean and reusable while leaving provider adapters and HTTP concerns in the infrastructure and API layers.

## Validation rules

The analysis service rejects invalid candle data before computation:

- candles must not be empty
- `high` must be greater than or equal to `low`
- `high` must be at least the maximum of `open` and `close`
- `low` must be at most the minimum of `open` and `close`
- volume must be non-negative
- candles must be ordered chronologically before analysis

## Indicator conventions

The implementation follows explicit conventions for deterministic, auditable calculations:

- SMA: arithmetic mean over the trailing close prices
- EMA: first close value used as the seed, then recursive EMA smoothing
- RSI: Wilder-style average gain and loss, with flat-loss cases resolving to a safe neutral value instead of invalid output
- MACD: EMA-based fast/slow difference with an EMA signal line
- Bollinger Bands: population standard deviation across the trailing period
- ATR: Wilder smoothing across true ranges
- Volume analysis: current volume against trailing-period average volume

## Strategy pattern

Strategy logic is isolated behind a registry object rather than embedded in the route layer. Each strategy returns:

- a strategy name
- a trend direction
- a brief rationale
- indicator values used to support the observation

This makes the analysis engine extensible without changing the API contract.

## Data contracts

The domain layer defines stable result objects for:

- `IndicatorConfig`
- `TrendDirection`
- `TechnicalAnalysisResult`
- per-indicator result payloads
- strategy observations

The API layer converts those domain objects into serializable dictionary/JSON payloads while preserving Decimal values as strings to prevent float drift or invalid JSON encoding.

## Example response shape

```json
{
  "symbol": "BTC",
  "timeframe": "1h",
  "timestamp": "2025-01-01T00:00:00Z",
  "trend": "BULLISH",
  "indicators": {
    "sma": { "period": 20, "value": "12345.67" },
    "ema": { "period": 12, "value": "12340.12" },
    "rsi": { "period": 14, "value": "61.25" }
  },
  "strategies": [
    {
      "strategy_name": "MovingAverageTrendStrategy",
      "direction": "BULLISH",
      "rationale": "Short-term trend is above the longer-term baseline.",
      "indicator_values": {
        "sma": "12345.67",
        "ema": "12340.12"
      }
    }
  ]
}
```

## Acceptance notes

This phase intentionally focuses on deterministic, explainable analysis rather than trade execution. The engine is designed to be extended with additional indicators or strategies without altering the provider boundary or API contract.
