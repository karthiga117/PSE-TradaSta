# TradaSta AI Backend

TradaSta AI is a Python FastAPI backend foundation for a future-ready trading intelligence platform. The repository now includes the Phase 1 foundation, the deterministic technical-analysis layer, the risk-management guardrail, and the Phase 6 trading-signal engine that orchestrates market data, strategy evaluation, and risk gating into explainable BUY/SELL/HOLD outputs.

## Technology stack

- Python 3.12+
- FastAPI
- Uvicorn
- Pydantic v2 and pydantic-settings
- pytest, pytest-asyncio, and httpx
- Ruff and MyPy

## Current capabilities

- Clean application bootstrap, config, logging, and exception handling
- Provider-independent market-data abstractions and a CoinGecko adapter
- Deterministic technical-analysis engine for SMA, EMA, RSI, MACD, Bollinger Bands, ATR, and volume analysis
- Strategy registry with deterministic sample strategies and trend classification
- Risk-management gate that evaluates stop loss, take profit, exposure, and drawdown constraints
- Trading Signal Engine that returns deterministic BUY/SELL/HOLD decisions with confidence, risk/reward, and explainable reasoning
- Thin FastAPI routes for price/OHLCV, technical analysis, risk evaluation, and signal generation

## Project structure

```text
TradaStaBackEnd/
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── analysis.py
│   │       ├── market_data.py
│   │       └── router.py
│   ├── application/
│   │   ├── market_data_service.py
│   │   └── technical_analysis/
│   │       ├── __init__.py
│   │       ├── service.py
│   │       └── strategies.py
│   ├── core/
│   │   ├── config.py
│   │   ├── dependencies.py
│   │   ├── exceptions.py
│   │   └── logging.py
│   ├── domain/
│   │   ├── market_data.py
│   │   └── technical_analysis/
│   │       ├── __init__.py
│   │       ├── indicators.py
│   │       └── models.py
│   ├── infrastructure/
│   │   └── market_data/
│   │       └── providers/
│   │           └── coingecko.py
│   ├── __init__.py
│   ├── main.py
│   └── health/
│       └── router.py
├── docs/
│   └── TECHNICAL_ANALYSIS_DESIGN.md
├── tests/
│   └── test_technical_analysis.py
├── .env.example
├── .gitignore
├── Dockerfile
├── pyproject.toml
├── README.md
└── .venv/
```

## Prerequisites

- Python 3.12+
- A virtual environment manager such as venv or uv
- Internet access for installing dependencies

## Local setup

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
# source .venv/bin/activate
python -m pip install -U pip
python -m pip install -e ".[dev]"
cp .env.example .env
```

## Environment configuration

Create a local `.env` file with values such as:

```env
APP_NAME=TradaSta AI
APP_VERSION=0.1.0
ENVIRONMENT=development
DEBUG=false
LOG_LEVEL=INFO
API_V1_PREFIX=/api/v1
```

Do not commit `.env` to version control.

## Run the application

```bash
uvicorn app.main:app --reload
```

The app listens on `http://localhost:8000` by default.

## API endpoints

- `GET /` - service status
- `GET /api/v1/health` - lightweight health check
- `GET /api/v1/market-data/{symbol}/price` - current price for a symbol
- `GET /api/v1/market-data/{symbol}/ohlcv` - normalized OHLCV candles for a symbol and timeframe
- `GET /api/v1/analysis/{symbol}` - deterministic technical-analysis output with indicators and strategy observations
- `POST /api/v1/risk/evaluate` - deterministic risk gate that approves or rejects proposed trades using configured portfolio, position-size, and drawdown limits
- `POST /api/v1/signals` - trading signal engine that combines market data, technical analysis, strategy direction, and risk validation into BUY/SELL/HOLD output
- `GET /docs` - interactive OpenAPI docs

## Example request

```bash
curl "http://localhost:8000/api/v1/analysis/BTC?timeframe=1h&limit=200"
```

The response includes:

- `trend` classification
- indicator values for SMA, EMA, RSI, MACD, Bollinger Bands, ATR, and volume analysis
- strategy observations generated from the deterministic strategy registry

### Signal generation example

```bash
curl -X POST "http://localhost:8000/api/v1/signals" \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "BTCUSDT",
    "timeframe": "1h",
    "strategy": "moving_average_trend",
    "account_equity": "10000",
    "current_exposure": "2000",
    "daily_loss": "100",
    "peak_equity": "10000",
    "current_equity": "9800",
    "open_positions": 2
  }'
```

The API returns a deterministic signal in the form `BUY`, `SELL`, or `HOLD`, with confidence, risk/reward, and a human-readable explanation. Risk validation remains mandatory before any BUY or SELL outcome is published.

## Run tests

```bash
pytest
```

## Code quality

```bash
ruff check app tests
mypy app
```

## Docker

```bash
docker build -t tradasta-backend .
docker run --rm -p 8000:8000 tradasta-backend
```
